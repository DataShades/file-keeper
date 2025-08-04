# from azure.storage.blob import generate_blob_sas, BlobSasPermissions

# def azure_signed_action(action, duration, location):
#     container, blob = location.split('/', 1)
#     perms = BlobSasPermissions()
#     if action == 'download': perms.read = True
#     elif action == 'upload': perms.write = True; perms.create = True
#     elif action == 'delete': perms.delete = True
#     else: raise ValueError('Unsupported action')

#     sas = generate_blob_sas(
#         account_name=...,
#         account_key=...,
#         container_name=container,
#         blob_name=blob,
#         permission=perms,
#         expiry=datetime.utcnow() + timedelta(seconds=duration)
#     )
#     return f"https://{account}.blob.core.windows.net/{container}/{blob}?{sas}"
