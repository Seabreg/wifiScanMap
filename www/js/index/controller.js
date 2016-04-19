'use strict';

(function() {
  
  class indexController {
    constructor($http, $scope, $location) {
      this.host = "";
      this.$location = $location
      
      this.$scope = $scope;
      this.$scope.link_status = false;
      this.$scope.display_wifis = true;
      this.$http = $http;
      
      this.position = new ol.source.Vector({});
      this.wifisSource = new ol.source.Vector({});
      this.stationsSource = new ol.source.Vector({});
      
      this.$scope.search_terms = this.$location.path().substring(1);
      
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
        })
        ],
        target: 'map',
        controls: ol.control.defaults({
          attributionOptions: /** @type {olx.control.AttributionOptions} */ ({
            collapsible: false
          })
        }),
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

      $scope.update_wifis = function() {
        if(self.$scope.display_wifis) {
          self.update_wifis();
        } else {
          self.wifisSource.clear();
        }
      }
      
      $scope.update_stations = function() {
        if(self.$scope.display_stations) {
          self.update_stations();
        } else {
          self.stationsSource.clear();
        }
      }
      
      $scope.search = function() {
        
        $location.path (self.$scope.search_terms);
        var pattern = new RegExp(self.$scope.search_terms,"i");
        if(self.$scope.display_wifis) {
          var features = self.wifisSource.getFeatures();
          for(var i in features) {
            if ('wifis' in features[i].getProperties()) {
              var hide = true;
              for(var j in features[i].getProperties().wifis) {
                var wifi = features[i].getProperties().wifis[j]
                if(pattern.test(wifi['bssid']) || pattern.test(wifi['essid']) || pattern.test(wifi['manufacturer'])) {
                  hide = false;
                }
              }
              if(hide) {
                var point = new ol.geom.Point( ol.proj.transform([0, 0 ], 'EPSG:4326', 'EPSG:3857'));
                features[i].setGeometry(point);
              } else {
                var point = new ol.geom.Point( ol.proj.transform([features[i].getProperties().wifis[0]['longitude'], features[i].getProperties().wifis[0]['latitude'] ], 'EPSG:4326', 'EPSG:3857'));
                features[i].setGeometry(point);
              }
            }
          }
        } else if(self.$scope.display_stations) {
          var features = self.stationsSource.getFeatures();
          for(var i in features) {
            if ('station' in features[i].getProperties()) {
              var hide = true;
              var station = features[i].getProperties().station
              if(pattern.test(station['bssid']) || pattern.test(station['manufacturer'])) {
                hide = false;
              }
              
              if(hide) {
                var point = new ol.geom.Point( ol.proj.transform([0, 0 ], 'EPSG:4326', 'EPSG:3857'));
                features[i].setGeometry(point);
              } else {
                var point = new ol.geom.Point( ol.proj.transform([station['longitude'], station['latitude'] ], 'EPSG:4326', 'EPSG:3857'));
                features[i].setGeometry(point);
              }
            }
          }
        }
      };
      
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
              html += "<li>"+ station["date"] + ' ' +station["manufacturer"] +"</li>";
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
        }
        
        if(response.data['position']['gps']['fix']) {
          var longitude = response.data['position']['gps']['longitude'];
          var latitude = response.data['position']['gps']['latitude'];
          var point = new ol.geom.Point( ol.proj.transform([longitude, latitude ], 'EPSG:4326', 'EPSG:3857'));
          self.gps.setGeometry(point);
        }
        setTimeout(self.update_status.bind( self ),1000);
      }, function errorCallback(response) {
        self.$scope.link_status = false;
        setTimeout(self.update_status.bind( self ),1000);
      });
    }
    
    
    update_stations() {
      this.stationsSource.clear();
      this.$http.get(this.host + '/stations.json').then(response => {
        this.stations = response.data
        for(var i in response.data) {
          var color = '#'+Math.random().toString(16).slice(-3);
          for(var r in response.data[i]['points']) {
            var res = response.data[i]['points'][r]
            var point = new ol.geom.Point( ol.proj.transform([res["longitude"], res["latitude"]], 'EPSG:4326', 'EPSG:3857'));
            var station = new ol.Feature({
              geometry: point,
              station : { bssid: i, latitude:res["latitude"], longitude:res["longitude"], manufacturer:response.data[i]['manufacturer'], date: res["date"], signal: res["signal"]}
            });
            var pointStyle = new ol.style.Style({
              image: new ol.style.Circle({
                //               fill: new ol.style.Fill({
                //                 color: color
                //               }),
                stroke: new ol.style.Stroke({
                  color: color,
                  width: 2
                }),
                radius: 4,
              })
            })
            station.setStyle(pointStyle);
            this.stationsSource.addFeature( station );
          }
        }
      });
    }
    
    update_wifis() {
      var wifis = [];
      var lastLat = -1;
      var lastLon = -1;
      var info = []
      this.wifisSource.clear();
      this.$http.get(this.host+'/wifis.json').then(response => {
        for(var w in response.data) {
          if(response.data[w]['latitude'] != lastLat || response.data[w]['longitude'] != lastLon ) {
            if(info.length > 0) {
              wifis.push(info);
            }
            info = [response.data[w]]
            lastLat = response.data[w]['latitude'];
            lastLon = response.data[w]['longitude'];
          } else {
            info.push(response.data[w]);
          }
        }
        for(var i in wifis ) {
          var lat = wifis[i][0]["latitude"];
          var lon = wifis[i][0]["longitude"];
          
          var len = wifis[i].length;
          
          var count = 0;
          
          for(var j in wifis[i]) {
            if(wifis[i][j]["encryption"]) {
              count++;
            }
          }
          
          var percent = count / len;
          var fill = new ol.style.Fill({
            color: "rgba(0,255,0,"+(1-percent)+")"
          });
          
          var color = "#3399CC";
          
          
          if(len > 1) {
            color = "#FF9933";
            
            if(len > 4) {
              color = "red";
            }
          }
          
          var stroke = new ol.style.Stroke({
            color: color,
            width: 1.25
          });
          
          var pointStyle = new ol.style.Style({
            image: new ol.style.Circle({
              fill: fill,
              stroke: stroke,
              radius: 5,
            })
          })
          
          var point = new ol.geom.Point( ol.proj.transform([lon, lat ], 'EPSG:4326', 'EPSG:3857'));
          
          var wifi = new ol.Feature({
            wifis:wifis[i],
            geometry: point,
          });
          wifi.setStyle(pointStyle);
          this.wifisSource.addFeature( wifi );
        }
        if(self.$location.path() != "")
        {
          self.$scope.search();
        }
      });
    }
    
    changeHost() {
      this.update_wifis();
      this.update_status();
    }
    
  }
  
  app.controller('indexController', function($http,$scope,$location) {
    return new indexController($http,$scope,$location);
  });
  
})();