# untitled-project
The docker-compose solution launches:

- elasticsearch cluster to store geospatial data [link](http://localhost:9200/)
- kibana to visualize and explore data [link](http://localhost:5601/)
    - The map is located on the left hand menu `Kibana->Maps->Regina`
- jupyter lab [link](http://localhost:8890/lab?)
    - password is `password`

## Install
Build using docker compose

`docker-compose build
`

Launch

`docker-compose up
`

## Getting Started

Once the solution is launched you will need to run the notebook `Load Data Scripts.ipynb` to pull data from the
different data sources. You won't need to run this again since elasticsearch will store the data on a volume on the local machine.
These scripts will also import pre-generated Kibana maps for exploring unique parks and businesses in Regina. 


### Genarating Maps

After you've loaded the data, you can use `Generate Maps.ipynb` to start 
generating html maps. Map outputs are saved in the `outputs/maps` directory.