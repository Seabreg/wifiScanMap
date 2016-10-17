# Bordeaux: a digital urban exploration

## Wifi Dataset properties


- dates 

   ````select min(date), max(date) from wifis limit  1````
   "2016-02-20 14:15:19"	"2016-10-11 13:40:33"

- Count

   ````select count(*) from wifis;````
   29494

   ````select count(*) from wifis where encryption = 0;````
   7044

- Probes request

select count(*) from probes;
118052

- Coverage:

  ![Coverage](results/coverage.png)

## What if you wanted to add some semantic to your map with some ...

- fast foods

   ![Fast Foods](results/fastfoods.png)

- hospitals

   ![hospitals](results/hospitals.png)
   
- universities

   ![universities](results/universities.png)

- Railroad stations

   ![railroad](results/railroad_stations.png)

- Public transports infrastructure

   ![tbc](results/tbc.png)

- Hotels

   ![hotels](results/hotels.png)

- Some french agencies ( Chambre de Commerce et d'Industrie de Bordeaux )

   ![ccib](results/ccib.png)

- The airport does not seems to be on the map but it should be somewhere around...

   ![airport](results/airport.png)
   

## Where people were connected before comming?

   ![bt](results/top_probes.png)

Mainly on public wifi, hotels and more than 633 from [Le Ceitya](http://www.hotel-leceitya.com/)

Public transport have their own infrastructure with 393 devices embedded within public buses looking for BUSTBC, and 108 devices within trams looking for SSID_TRAM and Depot_001.

You can even trace buses position

![buses](results/bus_date.png)


- 62 postmans using the [facteo](http://laposte.insa-rennes.fr/facteo/) service on a samsumg device


## What if you wanted to track people

### Through their bluetooth devices

   ![bt](results/bt.png)
   
   ![bt class](results/bt_class.png)   