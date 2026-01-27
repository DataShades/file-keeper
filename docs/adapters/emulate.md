# Emulate cloud providers with Docker

For local development and testing, you can emulate cloud providers using Docker
containers. This allows you to test your file-keeper integrations without
incurring costs or requiring access to real cloud resources.

Remember to adjust the port mappings and environment variables as needed for
your specific setup.

/// tab | MinIO (S3-compatible)

```sh
docker run -d -p 9000:9000 -p 9001:9001 \
    --name minio \
    -e MINIO_PUBLIC_ADDRESS=0.0.0.0:9000 \
    quay.io/minio/minio server /data --console-address ":9001"
```

| Attribute | Value                 |
|-----------|-----------------------|
| Endpoint  | http://127.0.0.1:9000 |
| Key       | `minioadmin`          |
| Secret    | `minioadmin`          |

///

/// tab | Azurite (Azure Blob Storage)

```sh
docker run -d -p 10000:10000 \
    --name azurite-blob \
    mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0 --skipApiVersionCheck
```

| Attribute | Value                                                                                      |
|-----------|--------------------------------------------------------------------------------------------|
| Endpoint  | http://127.0.0.1:10000                                                                     |
| Key       | `devstoreaccount1`                                                                         |
| Secret    | `Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==` |


///

/// tab | Fake GCS Server (Google Cloud Storage)

```sh
docker run -d -p 4443:4443 \
     --name gcs \
     fsouza/fake-gcs-server -scheme http
```


| Attribute | Value                 |
|-----------|-----------------------|
| Endpoint  | http://127.0.0.1:4443 |
| Key       | Not required          |
| Secret    | Not required          |

///
