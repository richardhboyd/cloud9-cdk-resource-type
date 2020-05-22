import inspect
import logging
from time import sleep
import json
import base64
from typing import Any, Mapping, MutableMapping, Optional
from functools import singledispatch

from cloudformation_cli_python_lib import (
    Action,
    HandlerErrorCode,
    OperationStatus,
    ProgressEvent,
    Resource,
    SessionProxy,
    exceptions,
)

from .interface import (
    ProvisioningStatus,
    EnvironmentCreated,
    RoleCreated,
    ProfileAttached,
    CommandSent,
    InstanceStable,
    ResizedInstance
)

from .models import ResourceHandlerRequest, ResourceModel

# Use this logger to forward log messages to CloudWatch Logs.
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
TYPE_NAME = "CDK::Cloud9::Environment"

resource = Resource(TYPE_NAME, ResourceModel)
test_entrypoint = resource.test_entrypoint

def ssm_ready(ssm_client, instance_id):
    try:
        response = ssm_client.describe_instance_information(Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}])
        LOG.info(response)
        return len(response['InstanceInformationList'])>=1
    except ssm_client.exceptions.InvalidInstanceId:
        return False

def get_name_from_request(request: ResourceHandlerRequest) -> str:
    if request.desiredResourceState.Name:
        return request.desiredResourceState.Name
    else:
        import hashlib
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y/%m/%d-%H:%M:%S").encode('utf-8')
        m = hashlib.sha256(timestamp).hexdigest()[:6]
        return "{}-{}".format(request.logicalResourceIdentifier, m)

def resize_ebs(instance_id: str, volume_size: int, ec2_client) -> None:
    instance = ec2_client.describe_instances(Filters=[{'Name': 'instance-id', 'Values': [instance_id]}])['Reservations'][0]['Instances'][0]
    block_volume_id = instance['BlockDeviceMappings'][0]['Ebs']['VolumeId']
    try:
        ec2_client.modify_volume(VolumeId=block_volume_id,Size=volume_size)
    except Exception as e:
        LOG.info(e)
        raise Exception(e)

def get_or_create_role(iam_client, role_name, instance_id, environment_id) -> str:
    try:
        response = iam_client.create_role(
            Path='/cdk/cloud9/environment',
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(
                {
                    'Version': '2012-10-17',
                    'Statement': {
                        'Effect': 'Allow',
                        'Principal': {'Service': 'ec2.amazonaws.com'},
                        'Action': 'sts:AssumeRole'
                    }
                }),
            Description='EC2 Instance Profile Role',
            Tags=[
                {
                    'Key': 'EC2 Instance',
                    'Value': instance_id
                },
                {
                    'Key': 'Cloud9 Environment',
                    'Value': environment_id
                },
            ]
        )
    except iam_client.exceptions.EntityAlreadyExistsException as _:
        response = iam_client.get_role(RoleName=role_name)
    return response['Role']['RoleName']

@singledispatch
def create(obj: ProvisioningStatus, request: ResourceHandlerRequest, callback_context: MutableMapping[str, Any], session: SessionProxy):
    LOG.info("starting NEW RESOURCE with request\n{}".format(request))
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=request.desiredResourceState,
        callbackContext=callback_context,
        callbackDelaySeconds=15
    )
    env_name = get_name_from_request(request)
    if request.desiredResourceState.OwnerArn:
        owner_arn = request.desiredResourceState.OwnerArn
    else:
        owner_arn = "arn:aws:iam::{}:root".format(session.client('sts').get_caller_identity()['Account'])
    response = session.client('cloud9').create_environment_ec2(
      ownerArn=owner_arn,
      name=env_name,
      instanceType=request.desiredResourceState.InstanceType,
      automaticStopTimeMinutes=30
    )
    LOG.info("environment id: {}".format(response['environmentId']))
    model: ResourceModel = request.desiredResourceState
    model.Name = env_name
    model.EnvironmentId = response['environmentId']
    progress.callbackContext["ENVIRONMENT_NAME"] = env_name
    progress.callbackContext["ENVIRONMENT_ID"] = response['environmentId']
    progress.callbackContext["LOCAL_STATUS"] = EnvironmentCreated()
    progress.status = OperationStatus.IN_PROGRESS
    progress.message = "Cloud9 Environment created"
    return progress

@create.register(EnvironmentCreated)
def get_environment_info(obj: ProvisioningStatus, request: ResourceHandlerRequest, callback_context: MutableMapping[str, Any], session: SessionProxy):
    LOG.info("starting ENVIRONMENT_CREATED with callback_context\n{}\nand request\n{}".format(callback_context, request))
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=request.desiredResourceState,
        callbackContext=callback_context,
        callbackDelaySeconds=15
    )
    environment_id = callback_context["ENVIRONMENT_ID"]
    LOG.info("environment id: {}".format(environment_id))
    try: 
        ec2_client = session.client("ec2")
        instance_filter = ec2_client.describe_instances(Filters=[{'Name':'tag:aws:cloud9:environment', 'Values': [environment_id]}])
        if len(instance_filter['Reservations']) < 1:
            LOG.info("instance not available from `describe instances` call")
            return progress
        if len(instance_filter['Reservations'][0]['Instances']) < 1:
            LOG.info("instance not available from `describe instances` call, part deux")
            return progress
        instance_id = instance_filter['Reservations'][0]['Instances'][0]['InstanceId']
        instance_state = instance_filter['Reservations'][0]['Instances'][0]['State']['Name']
        c9_client = session.client("cloud9")
        environment_status = c9_client.describe_environment_status(environmentId=environment_id)
        LOG.info("Checking Environment and instance status")
        if (environment_status['status'] == 'ready') and (instance_state == 'running'):
            LOG.info("environment is ready and instance is running")
            progress.resourceModel.InstanceId = instance_id
            progress.callbackContext["INSTANCE_ID"] = instance_id
            progress.message = "Cloud9 Environment is stable"
            progress.callbackDelaySeconds=0
            if request.desiredResourceState.EBSVolumeSize:
                progress.callbackContext["LOCAL_STATUS"] = InstanceStable()
            else:
                progress.callbackContext["LOCAL_STATUS"] = ResizedInstance()
            
    except Exception as e:
        LOG.info('throwing: {}'.format(e))
        raise(e)
    LOG.info("returning progress from ENVIRONMENT_CREATED {}".format(progress))
    return progress

@create.register(InstanceStable)
def handle_A(obj: ProvisioningStatus, request: ResourceHandlerRequest, callback_context: MutableMapping[str, Any], session: SessionProxy):
    LOG.info("starting INSTANCE_STABLE with callback_context\n{}\nand request\n{}".format(callback_context, request))
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=request.desiredResourceState,
        callbackContext=callback_context,
        callbackDelaySeconds=0
    )
    instance_id = callback_context["INSTANCE_ID"]
    try: 
        ec2_client = session.client("ec2")
        if request.desiredResourceState.EBSVolumeSize:
            resize_ebs(instance_id, int(request.desiredResourceState.EBSVolumeSize), ec2_client)
        progress.callbackContext["LOCAL_STATUS"] = ResizedInstance()
        progress.message = "Resized EBS Volume"
    except Exception as e:
        LOG.info('Can\'t resize instance: {}'.format(e))
        raise(e)
    LOG.info("returning progress from INSTANCE_STABLE {}".format(progress))
    return progress


@create.register(ResizedInstance)
def create_iam_role(obj: ProvisioningStatus, request: ResourceHandlerRequest, callback_context: MutableMapping[str, Any], session: SessionProxy):
    LOG.info("starting CREATE_IAM_ROLE with callback_context\n{}\nand request\n{}".format(callback_context, request))
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=request.desiredResourceState,
        callbackContext=callback_context,
        callbackDelaySeconds=1
    )
    environment_id = callback_context["ENVIRONMENT_ID"]
    instance_id = callback_context["INSTANCE_ID"]
    environment_id = callback_context["ENVIRONMENT_ID"]
    environment_name = callback_context["ENVIRONMENT_NAME"]
    iam_client = session.client("iam")
    role_name = get_or_create_role(iam_client, f'{environment_name}-InstanceProfileRole', instance_id, environment_id)
    if request.desiredResourceState.Cloud9InstancePolicy:
        LOG.debug(f'attempting to add the following inline policy: {request.desiredResourceState.Cloud9InstancePolicy._serialize()}')
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=request.desiredResourceState.Cloud9InstancePolicy.PolicyName,
            PolicyDocument=json.dumps(request.desiredResourceState.Cloud9InstancePolicy.PolicyDocument._serialize())
        )
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn='arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
    )
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn='arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy'
    )
    
    LOG.info("Creating Instance Profile")
    create_instance_profile_response = iam_client.create_instance_profile(
        InstanceProfileName=f'{environment_name}-InstanceProfile',
        Path='/cdk/cloud9/environment'
    )
    LOG.info("Attatching Role to Instance Profile")
    iam_client.add_role_to_instance_profile(
        InstanceProfileName=f'{environment_name}-InstanceProfile',
        RoleName=role_name
    )
    progress.callbackContext["LOCAL_STATUS"] = RoleCreated()
    progress.callbackContext["INSTANCE_PROFILE_ARN"] = create_instance_profile_response['InstanceProfile']['Arn']
    LOG.info("returning progress from CREATE_IAM_ROLE {}".format(progress))
    return progress

@create.register(RoleCreated)
def create_and_attach_instance_profile(obj: ProvisioningStatus, request: ResourceHandlerRequest, callback_context: MutableMapping[str, Any], session: SessionProxy):
    LOG.info("starting ATTACH_INSTANCE_PROFILE with callback_context\n{}\nand request\n{}".format(callback_context, request))
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=request.desiredResourceState,
        callbackContext=callback_context,
        callbackDelaySeconds=30
    )
    instance_profile_arn = callback_context["INSTANCE_PROFILE_ARN"]
    instance_id = callback_context["INSTANCE_ID"]
    try:
        ec2_client = session.client('ec2')
        associate_profile_response = ec2_client.associate_iam_instance_profile(
            IamInstanceProfile={'Arn': instance_profile_arn},
            InstanceId=instance_id
        )
        callback_context["ASSOCIATION_ID"] = associate_profile_response['IamInstanceProfileAssociation']['AssociationId']
        progress.callbackContext["LOCAL_STATUS"] = ProfileAttached()
    except Exception as e:
        print(e)
    LOG.info("returning progress from ATTACH_INSTANCE_PROFILE {}".format(progress))
    return progress

@create.register(ProfileAttached)
def send_command(obj: ProvisioningStatus, request: ResourceHandlerRequest, callback_context: MutableMapping[str, Any], session: SessionProxy):
    LOG.info("starting SEND_COMMAND with callback_context\n{}\nand request\n{}".format(callback_context, request))
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=request.desiredResourceState,
        callbackContext=callback_context,
        callbackDelaySeconds=0
    )
    instance_id = callback_context["INSTANCE_ID"]
    ssm_client = session.client('ssm')
    
    if not ssm_ready(ssm_client, instance_id):
        progress.callbackDelaySeconds=180
        return progress
    with open('./cdk_cloud9_environment/run_command.sh', 'r') as myfile:
      commands = myfile.read()
    
    LOG.info("Sending command to %s : %s" % (instance_id, commands))
    try:
        send_command_response = ssm_client.send_command(
            InstanceIds=[instance_id], 
            DocumentName='AWS-RunShellScript', 
            Parameters={'commands': commands.split('\n')},
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': f'ssm-output-{instance_id}',
                'CloudWatchOutputEnabled': True
            }
        )
        progress.callbackContext["RUN_COMMAND_ID"] = send_command_response['Command']['CommandId']
        progress.callbackContext["LOCAL_STATUS"] = CommandSent()
    except ssm_client.exceptions.InvalidInstanceId:
        LOG.info("Failed to execute SSM command. This happens some times when the box isn't ready yet. we'll retry in a minute.")
    LOG.info("returning progress from SEND_COMMAND {}".format(progress))
    return progress

@create.register(CommandSent)
def stabilize(obj: ProvisioningStatus, request: ResourceHandlerRequest, callback_context: MutableMapping[str, Any], session: SessionProxy):
    LOG.info("starting STABILIZED with callback_context\n{}\nand request\n{}".format(callback_context, request))
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=request.desiredResourceState,
        callbackContext=callback_context,
        callbackDelaySeconds=60
    )
    command_id = callback_context["RUN_COMMAND_ID"]
    instance_id = callback_context["INSTANCE_ID"]
    ssm_client = session.client('ssm')
    response = ssm_client.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    if response['Status'] in ['Pending', 'InProgress', 'Delayed']:
        return progress
    else:
        progress.status = OperationStatus.SUCCESS
    LOG.info("returning progress from STABILIZED {}".format(progress))
    return progress

@resource.handler(Action.CREATE)
def create_handler(
    session: Optional[SessionProxy], 
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    try:
        if isinstance(session, SessionProxy):
            if callback_context:
                test_thing = ProvisioningStatus._deserialize(callback_context.get("LOCAL_STATUS"))
            else:
                test_thing = None
            progress = create(test_thing, request, callback_context, session)
            LOG.info(f"returning from dispatch: {progress}")
            return progress
    except TypeError as e:
        raise exceptions.InternalFailure(f"was not expecting type {e}")


@resource.handler(Action.UPDATE)
def update_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=model,
    )
    progress.status = OperationStatus.SUCCESS
    return progress


@resource.handler(Action.DELETE)
def delete_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=model,
    )
    iam_client = session.client("iam")
    roles = iam_client.list_roles(PathPrefix='/cdk/cloud9/environment')
    for role in roles['Roles']:
        role_info = iam_client.get_role(role['RoleName'])
        if 'Tags' in role_info['Role']:
            tags = role_info['Role']['Tags']
            for tag in tags:
                if tag['Key'] == 'Cloud9 Environment' and tag['value'] == request.desiredResourceState.EnvironmentId:
                    instance_profiles = iam_client.list_instance_profiles_for_role(RoleName=role['RoleName'])
                    for instance_profile in instance_profiles['InstanceProfiles']:
                        iam_client.delete_instance_profile(InstanceProfileName=instance_profile['InstanceProfileName'])
                    iam_client.delete_role(RoleName=role['RoleName'])
    c9_client = session.client("cloud9")
    try:
        LOG.info(f"request: {request}")
        LOG.info(f"request: {callback_context}")
        c9_client.delete_environment(environmentId=request.desiredResourceState.EnvironmentId)
        progress.status = OperationStatus.SUCCESS
    except Exception as e:
        LOG.info(f"failed to delete environment: {e}")
        progress.status = OperationStatus.FAILED
    return progress


@resource.handler(Action.READ)
def read_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState
    # TODO: put code here
    return ProgressEvent(
        status=OperationStatus.SUCCESS,
        resourceModel=model,
    )


@resource.handler(Action.LIST)
def list_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    # TODO: put code here
    return ProgressEvent(
        status=OperationStatus.SUCCESS,
        resourceModels=[],
    )
