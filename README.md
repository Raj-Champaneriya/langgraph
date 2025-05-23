# Learning Repo

This is learning repo to learn lang-graph from [Free Code Camp](https://www.youtube.com/watch?v=jGg_1h0qzaM)

Started with snippets
Then graphs
Then experimented bots
And exposed working bot to copilot

## Progress

* 4/10 agents implemented
* basic copilot is built

## Commands

``` bash

pip install -r requirements.txt

python run_with_mypy.py snippets/any.py 
python run_with_mypy.py graphs/graph1.py

python graphs/graph1.py

docker run --detach --publish 8081:8081 --publish 1234:1234 mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-preview --protocol https

copilot
cd copilot/frontend/my-chat-app
npm start

cd copilot/backend
python main.py    

```

References:
https://learn.microsoft.com/en-us/azure/cosmos-db/emulator-linux
http://localhost:1234/
https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/quickstart-python