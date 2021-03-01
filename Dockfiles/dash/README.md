# Dash Demo

## Introduction

This is a container to run ePython dash demo


## Testing Locally

### Run dash in gunicorn

```
gunicorn --workers 2 app:server
```

### Run in Container under ECS environment

Dependency library

```
cp -rf ../../tsdb/ .
```

Start docke-compose

```
docker-compose up
```

More details here: https://aws.amazon.com/blogs/compute/a-guide-to-locally-testing-containers-with-amazon-ecs-local-endpoints-and-docker-compose/

Now point browser at http://[::1]:8080/docs

Notice WSL2 binds localhost on IPV6 address.

## Deploying


### Building the container

```
docker build --tag epython-dash-demo:1.0 .
```

### Authenticating ECR

Replace <account_id> with AWS account id.

```
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.eu-west-1.amazonaws.com
```

### Create a repository

```
aws ecr create-repository \
    --repository-name epython-dash-demo \
    --image-scanning-configuration scanOnPush=true \
    --region eu-west-1
```

### Tag image

```
docker tag epython-dash-demo:1.0 <aws_account_id>.dkr.ecr.eu-west-1.amazonaws.com/epython-dash-demo:latest
```

### Push the image

```
docker push <aws_account_id>.dkr.ecr.eu-west-1.amazonaws.com/epython-dash-demo:latest
```