# v3 : Add Product Images and Use S3

**Objective:**  
Enhance the application by adding the ability to upload and store product images in **AWS S3**, and retrieve those images when product details are requested.

Installation:

Follow the install guide specified in app_v1.0 README.md

- The products endpoint now supports the request body to have an image to be upaloaded along with the product parameters.
- The image is uploaded to an AWS S3 bucket and the URL is uploaded to the products schema in RDS database.

![1](../assets/6.png)

- We use the methods provided in `boto3` package to access our bucket. Specify the access tokens and URI in the .env file in the application directory.
- Proper security ACL's are specified for each image and can be only accessed by public for reading the object.

Bucket policy :
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Statement1",
            "Effect": "Allow",
            "Principal": {
                "AWS": "*"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::cakeappbucket/*"
        }
    ]
}
```