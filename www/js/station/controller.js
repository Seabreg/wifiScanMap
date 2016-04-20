'use strict';

(function() {
  
  class stationController {
    constructor($http, $scope, $location) {
      this.host = "";
      this.$location = $location
      
      this.$scope = $scope;
      this.$scope.bssid = "";
      this.$scope.link_status = false;
      var search = this.$location.search()
      if(search.bssid != undefined) {
        this.$scope.bssid = search.bssid;
      }
      this.$http = $http;

      var self = this;
      this.$scope.update_station = function () {
        self.update_station();
      }
      
      this.position = new ol.source.Vector({});
      this.wifisSource = new ol.source.Vector({});
      this.stationsSource = new ol.source.Vector({});
      this.bt_stationsSource = new ol.source.Vector({});

      
      this.map = new ol.Map({
        layers: [
        new ol.layer.Tile({
          source: new ol.source.OSM()
        }),
        new ol.layer.Vector({
          source: this.position,
        }),
        new ol.layer.Vector({
          source: this.wifisSource,
        }),
        new ol.layer.Vector({
          source: this.stationsSource,
        }),
        new ol.layer.Vector({
          source: this.bt_stationsSource,
        })
        ],
        target: 'map',
//         controls: ol.control.defaults({
//           attributionOptions: /** @type {olx.control.AttributionOptions} */ ({
//             collapsible: false
//           })
//         }),
        view: new ol.View({
          center: ol.proj.transform([-0.576901, 44.837325 ], 'EPSG:4326', 'EPSG:3857'),
                          zoom: 15
        })
      });
      
      var pointStyle = new ol.style.Style({
        image: new ol.style.Circle({
          fill: new ol.style.Fill({
            color: 'red'
          }),
          stroke: new ol.style.Stroke({
            color: 'red',
            width: 1.25
          }),
          radius: 8,
        })
      })
      
      var pointStyleWifi  = new ol.style.Style({
        image: new ol.style.Circle({
          fill: new ol.style.Fill({
            color: 'blue'
          }),
          stroke: new ol.style.Stroke({
            color: 'blue',
            width: 1.25
          }),
          radius: 8,
        })
      })
      
      var point = new ol.geom.Point( ol.proj.transform([0, 0 ], 'EPSG:4326', 'EPSG:3857'));
      
      this.gps = new ol.Feature({
        geometry: point
      });
      this.wifi = new ol.Feature({
        geometry: point
      });
      
      this.gps.setStyle(pointStyle);
      this.wifi.setStyle(pointStyleWifi);
      
      this.position.addFeature( this.gps );
      this.position.addFeature( this.wifi );
      
      
      
      
      self = this
      
      $scope.center = function() {
        var latitude;
        var longitude;
        var center = false;
        if(self.$scope.status['position']['gps']['fix']) {
          latitude = self.$scope.status['position']['gps']['latitude'];
          longitude = self.$scope.status['position']['gps']['longitude'];
          center = true;
        } else if(self.$scope.status['position']['wifi']['fix']) {
          latitude = self.$scope.status['position']['wifi']['latitude'];
          longitude = self.$scope.status['position']['wifi']['longitude'];
          center = true;
        }
        
        if(center) {
          self.map.getView().setCenter(ol.proj.transform([longitude, latitude ], 'EPSG:4326', 'EPSG:3857'));
        }
      };
      
      $scope.changeHost = function() {
        self.host = self.$scope.map.host;
        self.changeHost();
      }

 
      
      this.map.getViewport().addEventListener('click', function (e) {
        e.preventDefault();
        
        
        var feature = self.map.forEachFeatureAtPixel(self.map.getEventPixel(e),
                                                     function (feature, layer) {
                                                       return feature;
                                                     });
        if (feature) {
          var html = "";
          if ('wifis' in feature.getProperties()) {
            var wifis = feature.getProperties().wifis;
            for(var i in wifis) {
              var encryption = "secure";
              if(wifis[i]["encryption"] == 0) {
                encryption = "open";
              }
              html += "<li class="+encryption+" >"+ wifis[i]["essid"] +"</li>";
            }
          } else {
            if ('station' in feature.getProperties()) {
              var station = feature.getProperties().station;
              html += "<li>"+ station["date"] + '<br/>' + station["name"] + ' ' +station["manufacturer"] +"</li>";
            }
          }
          
         
          $("#wifis-list").html(html);
          $("#left-pannel").show();
        } else {
          $("#left-pannel").hide(); 
        }
      });
      
      this.changeHost();
    }
    
    update_status() {
      var self = this;
      this.$http.get(this.host+'/status.json').then(response => {
        self.$scope.status = response.data;
        self.$scope.link_status = true;
        
        if(response.data['position']['wifi']['fix']) {
          var longitude = response.data['position']['wifi']['longitude'];
          var latitude = response.data['position']['wifi']['latitude'];
          var point = new ol.geom.Point( ol.proj.transform([longitude, latitude ], 'EPSG:4326', 'EPSG:3857'));
          self.wifi.setGeometry(point);
          self.$scope.status['position']['wifi']['accuracy'] = Math.round(self.$scope.status['position']['wifi']['accuracy']);
        }
        
        if(response.data['position']['gps']['fix']) {
          var longitude = response.data['position']['gps']['longitude'];
          var latitude = response.data['position']['gps']['latitude'];
          var point = new ol.geom.Point( ol.proj.transform([longitude, latitude ], 'EPSG:4326', 'EPSG:3857'));
          self.gps.setGeometry(point);
          self.$scope.status['position']['gps']['accuracy'] = Math.round(self.$scope.status['position']['gps']['accuracy']);
        }
        setTimeout(self.update_status.bind( self ),1000);
      }, function errorCallback(response) {
        self.$scope.link_status = false;
        setTimeout(self.update_status.bind( self ),1000);
      });
    }
    
    
    update_station() {
      this.$location.search('bssid', this.$scope.bssid);
      if(this.$scope.bssid != "") {
        this.$http.get(this.host+'/station.json?bssid='+this.$scope.bssid).then(response => {
          this.$scope.station = response.data;
          this.stationsSource.clear();
          for(var i in response.data['traces']) {
            var trace = response.data['traces'][i]
            var point = new ol.geom.Point( ol.proj.transform([trace['longitude'], trace['latitude']], 'EPSG:4326', 'EPSG:3857'));
            var station = new ol.Feature({
              geometry: point,
              station : trace
            });
            var pointStyle = new ol.style.Style({
              image: new ol.style.Circle({
                //               fill: new ol.style.Fill({
                //                 color: color
                //               }),
                stroke: new ol.style.Stroke({
                  color: 'red',
                  width: 2
                }),
                radius: 4,
              })
            })
            station.setStyle(pointStyle);
            this.stationsSource.addFeature( station );
            this.map.getView().setCenter(ol.proj.transform([trace['longitude'], trace['latitude']], 'EPSG:4326', 'EPSG:3857'));
          }
          
          this.wifisSource.clear();
          for(var i in response.data['wifis']) {
            var wifi = response.data['wifis'][i]
            var point = new ol.geom.Point( ol.proj.transform([wifi[4], wifi[5]], 'EPSG:4326', 'EPSG:3857'));
            var station = new ol.Feature({
              geometry: point,
              station : trace
            });
            var pointStyle = new ol.style.Style({
              image: new ol.style.Circle({
                //               fill: new ol.style.Fill({
                //                 color: color
                //               }),
                stroke: new ol.style.Stroke({
                  color: 'green',
                  width: 2
                }),
                radius: 4,
              })
            })
            station.setStyle(pointStyle);
            this.wifisSource.addFeature( station );
          }
        }, function errorCallback(response) {
        });
      }
    }
    
    changeHost() {
      this.update_status();
      this.update_station();
    }
    
  }
  
  app.controller('stationController', function($http,$scope,$location) {
    return new stationController($http,$scope,$location);
  });
  
})();