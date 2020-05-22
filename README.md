# CDK::Cloud9::Environment

Run these commands. Execution permissions ARE NOT SCOPED!

```bash
cat <<EOT > Test-Role-Trust-Policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "cloudformation.amazonaws.com",
          "resources.cloudformation.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOT

cat <<EOT > CFNMetricsPolicy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:PutLogEvents",
                "cloudwatch:ListMetrics",
                "cloudwatch:PutMetricData"
            ],
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
EOT

cat <<EOT > ExecutionPolicy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": ["*"],
      "Resource": ["*"],
      "Effect": "Allow"
    }
  ]
}
EOT

cat <<EOT > Template.yaml
AWSTemplateFormatVersion: 2010-09-09
Parameters:
  OwnerArn:
    Type: String
Resources:
  IAMTest:
    Type: CDK::Cloud9::Environment
    Properties:
      InstanceType: c5.large
      EBSVolumeSize: 50
      OwnerArn: !Ref OwnerArn
      Cloud9InstancePolicy:
        PolicyName: "MyInstancePolicy"
        PolicyDocument:
          Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - "*"
              Resource:
                - "*"
EOT



PROFILE=burner2
OWNER_ARN=$(aws sts get-caller-identity --query "Arn" --output text --profile $PROFILE)
ROLE_RESPONSE=$(aws iam create-role --role-name CloudFormationManagedUplo-LogAndMetricsDeliveryRol-1SKOPR6D2P648 --assume-role-policy-document file://Test-Role-Trust-Policy.json --output text --query "Role.[RoleName, Arn]" --profile $PROFILE)
set -- $ROLE_RESPONSE
ROLE_NAME=$1
ROLE_ARN=$2

EXECUTION_ROLE_RESPONSE=$(aws iam create-role --role-name ExecutionRoleForResourceProvider --assume-role-policy-document file://Test-Role-Trust-Policy.json --output text --query "Role.[RoleName, Arn]" --profile $PROFILE)
set -- $EXECUTION_ROLE_RESPONSE
EXECUTION_ROLE_NAME=$1
EXECUTION_ROLE_ARN=$2

aws iam put-role-policy --role-name $EXECUTION_ROLE_NAME --policy-name ExecutionPolicy --policy-document file://ExecutionPolicy.json --profile $PROFILE

aws iam put-role-policy --role-name $ROLE_NAME --policy-name LogAndMetricsDeliveryRolePolicy --policy-document file://CFNMetricsPolicy.json --profile $PROFILE

# Register the type
REG_TOKEN=$(aws cloudformation register-type --execution-role-arn ${EXECUTION_ROLE_ARN} --logging-config LogRoleArn=${ROLE_ARN},LogGroupName=richard-cloud9-environment-logs --type RESOURCE --type-name CDK::Cloud9::Environment --schema-handler-package s3://rhb-blog/provider-types/cdk-cloud9-environment.zip --query "RegistrationToken" --output text --profile $PROFILE)

# Once this command returns 'COMPLETE' you can run the final command.
aws cloudformation describe-type-registration --registration-token $REG_TOKEN  --query "ProgressStatus" --profile $PROFILE
# Wait for this to finish

aws cloudformation deploy --template-file ./Template.yaml --stack-name Late-Otter01 --parameter-overrides OwnerArn=$OWNER_ARN --profile $PROFILE
```