from azure.cosmos import CosmosClient, PartitionKey, exceptions
import os

# Emulator endpoint and key (default values)
endpoint = "https://localhost:8081/"
key = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="

# Disable SSL verification for emulator (since it uses self-signed cert)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize Cosmos client
client = CosmosClient(endpoint, key, connection_verify=False)

# Create database if not exists
database_name = 'TestDatabase'
database = client.create_database_if_not_exists(id=database_name)

# Create container if not exists
container_name = 'TestContainer'
container = database.create_container_if_not_exists(
    id=container_name,
    partition_key=PartitionKey(path='/id'),
    offer_throughput=400
)

# Insert a record
item = {
    'id': '1',
    'name': 'John Doe',
    'email': 'john.doe@example.com'
}

container.upsert_item(item)
print("Item inserted successfully.")

# Read the record back
read_item = container.read_item(item='1', partition_key='1')
print("Item read successfully:")
print(read_item)