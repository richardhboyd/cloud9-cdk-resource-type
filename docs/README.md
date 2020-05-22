# CDK::Cloud9::Environment

An example resource schema demonstrating some basic constructs and validation rules.

## Syntax

To declare this entity in your AWS CloudFormation template, use the following syntax:

### JSON

<pre>
{
    "Type" : "CDK::Cloud9::Environment",
    "Properties" : {
        "<a href="#name" title="Name">Name</a>" : <i>String</i>,
        "<a href="#instancetype" title="InstanceType">InstanceType</a>" : <i>String</i>,
        "<a href="#description" title="Description">Description</a>" : <i>String</i>,
        "<a href="#ebsvolumesize" title="EBSVolumeSize">EBSVolumeSize</a>" : <i>Double</i>,
        "<a href="#ownerarn" title="OwnerArn">OwnerArn</a>" : <i>String</i>,
        "<a href="#cloud9instancepolicy" title="Cloud9InstancePolicy">Cloud9InstancePolicy</a>" : <i><a href="cloud9instancepolicy.md">Cloud9InstancePolicy</a></i>
    }
}
</pre>

### YAML

<pre>
Type: CDK::Cloud9::Environment
Properties:
    <a href="#name" title="Name">Name</a>: <i>String</i>
    <a href="#instancetype" title="InstanceType">InstanceType</a>: <i>String</i>
    <a href="#description" title="Description">Description</a>: <i>String</i>
    <a href="#ebsvolumesize" title="EBSVolumeSize">EBSVolumeSize</a>: <i>Double</i>
    <a href="#ownerarn" title="OwnerArn">OwnerArn</a>: <i>String</i>
    <a href="#cloud9instancepolicy" title="Cloud9InstancePolicy">Cloud9InstancePolicy</a>: <i><a href="cloud9instancepolicy.md">Cloud9InstancePolicy</a></i>
</pre>

## Properties

#### Name

The name to give to the Cloud9 Environment.

_Required_: No

_Type_: String

_Minimum_: <code>3</code>

_Maximum_: <code>50</code>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### InstanceType

The EC2 instance type to use.

_Required_: Yes

_Type_: String

_Pattern_: <code>^[a-z][1-9][.][a-z0-9]+$</code>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### Description

The description of the TPS report is an optional element.

_Required_: No

_Type_: String

_Minimum_: <code>20</code>

_Maximum_: <code>250</code>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### EBSVolumeSize

The size for the underlying EBS Volume.

_Required_: No

_Type_: Double

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### OwnerArn

Owner of the Cloud9 Environment. If not specified, it will be the root of the account.

_Required_: No

_Type_: String

_Pattern_: <code>^arn:aws:(iam|sts)::\d+:(root|(user\/[\w+=/:,.@-]{1,64}|federated-user\/[\w+=/:,.@-]{2,32}|assumed-role\/[\w+=:,.@-]{1,64}\/[\w+=,.@-]{1,64}))$</code>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### Cloud9InstancePolicy

_Required_: No

_Type_: <a href="cloud9instancepolicy.md">Cloud9InstancePolicy</a>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

## Return Values

### Ref

When you pass the logical ID of this resource to the intrinsic `Ref` function, Ref returns the EnvironmentId.

### Fn::GetAtt

The `Fn::GetAtt` intrinsic function returns a value for a specified attribute of this type. The following are the available attributes and sample return values.

For more information about using the `Fn::GetAtt` intrinsic function, see [Fn::GetAtt](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-getatt.html).

#### InstanceId

EC2 Instance Id used by the underlying EC2 instance.

#### EnvironmentId

Cloud9 Environment Id

