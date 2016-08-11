'use strict';

(function() {
  
  class indexController {
    constructor($http, $scope, $location) {
      this.host = "";
      this.$location = $location
      
      this.$scope = $scope;
      this.$scope.link_status = false;
      var search = this.$location.search()
      if(jQuery.isEmptyObject(search)) {
        this.$scope.display_wifis = true;
        this.$scope.search_terms = ""
      } else {
        if(search.wifis != undefined) {
          this.$scope.display_wifis = search.wifis == "true";
        }
        if(search.stations != undefined) {
          this.$scope.display_stations = search.stations == "true";
        }
        if(search.bt_stations != undefined) {
          this.$scope.display_bt_stations = search.bt_stations == "true";
        }
        if(search.terms != undefined) {
          this.$scope.search_terms =  search.terms;
        }
      }
      this.$http = $http;

      
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
      
      $scope.delete = function(bssid, essid) {
        console.log("====");
        console.log(bssid);
      }
      
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
      
      var box = this.map.getView().calculateExtent(this.map.getSize());
      this.bottom_right = ol.proj.transform([box[0], box[1]], 'EPSG:3857', 'EPSG:4326');
      this.upper_left = ol.proj.transform([box[2], box[3]], 'EPSG:3857', 'EPSG:4326');
      
      $scope.changeHost = function() {
        self.host = self.$scope.map.host;
        self.changeHost();
      }

      $scope.update_wifis = function() {
        if(self.$scope.display_wifis) {
          $location.search('wifis', "true");
          self.update_wifis();
        } else {
          $location.search('wifis', "false");
          self.wifisSource.clear();
        }
      }
      
      $scope.update_stations = function() {
        if(self.$scope.display_stations) {
          $location.search('stations', "true");
          self.update_stations();
        } else {
          $location.search('stations', "false");
          self.stationsSource.clear();
        }
      }
      
      $scope.update_bt_stations = function() {
        if(self.$scope.display_bt_stations) {
          $location.search('bt_stations', "true");
          self.update_bt_stations();
        } else {
          $location.search('bt_stations', "false");
          self.bt_stationsSource.clear();
        }
      }
      
      $scope.search = function() {
        
        $location.search('terms', self.$scope.search_terms);
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
        }  else if(self.$scope.display_bt_stations) {
          var features = self.bt_stationsSource.getFeatures();
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
        
        
        var html = "";
        var feature = self.map.forEachFeatureAtPixel(self.map.getEventPixel(e),
            function (feature, layer) {
              if ('wifis' in feature.getProperties()) {
                var wifis = feature.getProperties().wifis;
                for(var i in wifis) {
                  var encryption = "secure";
                  if(wifis[i]["encryption"] == 0) {
                    encryption = "open";
                  }
                  html += '<li class="'+encryption+'" >'+ wifis[i]["essid"] + ' ' + wifis[i]["bssid"] +' <a class="fa fa-minus-circle" href="/delete.json?bssid='+wifis[i]["bssid"]+'&essid='+wifis[i]["essid"]+'" >delete</a><hr/></li>';
                }
              } else {
                if ('station' in feature.getProperties()) {
                  var station = feature.getProperties().station;
                  var name = ''
                  var logo = ''
                  if(station["name"] != undefined) {
                    name = station["name"]
                    logo = '<div class="device-type '+station["class_description"]+'" ></div>';
                  }
                  html += "<li>"+ station["date"] + '<br/> <a href=/station.html#?bssid=' + station["bssid"] + ">" + station["bssid"] +'</a><br/>' + logo + name + ' ' +station["manufacturer"] +"<hr/></li>";
                }
              }
            });
        if (html != "") {
          $("#wifis-list").html(html);
          $("#left-pannel").show();
        } else {
          $("#left-pannel").hide(); 
        }
      });
      
      this.changeHost();
      this.move_timer = false;
      this.map.on('moveend', this.map_moveend, this)
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
    
    
    update_stations() {
      $("#loading-container").show();
      this.stationsSource.clear();
      
      this.$http.get(this.host+'/stations.json?search=latitude > '+this.bottom_right[1]+' and longitude > '+this.bottom_right[0]+' and latitude < '+this.upper_left[1]+' and longitude < '+this.upper_left[0]).then(response => {
        this.colors = {};
        
        for(var i in response.data) {
          try {
            if(this.colors[response.data[i]['bssid']] == undefined) {
              this.colors[response.data[i]['bssid']] = '#'+Math.random().toString(16).slice(-3);
            }

            var point = new ol.geom.Point( ol.proj.transform([response.data[i]["longitude"], response.data[i]["latitude"]], 'EPSG:4326', 'EPSG:3857'));
              var station = new ol.Feature({
                geometry: point,
                station : response.data[i]
              });
              var pointStyle = new ol.style.Style({
                image: new ol.style.Circle({
                  //               fill: new ol.style.Fill({
                  //                 color: color
                  //               }),
                  stroke: new ol.style.Stroke({
                    color: this.colors[response.data[i]['bssid']],
                    width: 2
                  }),
                  radius: 4,
                })
              })
              station.setStyle(pointStyle);
              this.stationsSource.addFeature( station );
          } catch(e) {
            console.log(e);
          }
        }
        if(self.$location.search('terms') != undefined)
        {
          self.$scope.search();
        }
        $("#loading-container").hide();
      });
    }
    
    update_bt_stations() {
      $("#loading-container").show();
      this.bt_stationsSource.clear();
      this.$http.get(this.host + '/bt_stations.json').then(response => {
        this.colors = {};
        
        for(var i in response.data) {
          
          if(this.colors[response.data[i]['bssid']] == undefined) {
            this.colors[response.data[i]['bssid']] = '#'+Math.random().toString(16).slice(-3);
          }
          try {
            var point = new ol.geom.Point( ol.proj.transform([response.data[i]["longitude"], response.data[i]["latitude"]], 'EPSG:4326', 'EPSG:3857'));
            var station = new ol.Feature({
              geometry: point,
              station : response.data[i]
            });
            var pointStyle = new ol.style.Style({
              image: new ol.style.Circle({
                //               fill: new ol.style.Fill({
                //                 color: color
                //               }),
                stroke: new ol.style.Stroke({
                  color: this.colors[response.data[i]['bssid']],
                  width: 2
                }),
                radius: 4,
              })
            })
            station.setStyle(pointStyle);
            this.bt_stationsSource.addFeature( station );
          } catch(e) {
            console.log(e);
          }
        }
        if(self.$location.search('terms') != undefined)
        {
          self.$scope.search();
        }
        $("#loading-container").hide();
      });
    }
    
    update_wifis() {
      $("#loading-container").show();
      var wifis = [];
      var lastLat = -1;
      var lastLon = -1;
      var info = []
      this.wifisSource.clear();
      this.$http.get(this.host+'/wifis.json?lat='+this.bottom_right[1]+'&lon='+this.bottom_right[0]+'&lat1='+this.upper_left[1]+'&lon1='+this.upper_left[0]).then(response => {
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
        if(info.length > 0) {
          wifis.push(info);
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
        if(self.$location.search('terms') != undefined)
        {
          self.$scope.search();
        }
        $("#loading-container").hide();
      });
    }
    
    changeHost() {
      this.$scope.update_wifis();
      this.$scope.update_stations();
      this.$scope.update_bt_stations();
      this.update_status();
    }
    
    map_reload() {
      this.$scope.update_wifis();
      this.$scope.update_stations();
      this.$scope.update_bt_stations();
    }
    
    map_moveend() {
      
      var box = this.map.getView().calculateExtent(this.map.getSize());
      this.bottom_right = ol.proj.transform([box[0], box[1]], 'EPSG:3857', 'EPSG:4326');
      this.upper_left = ol.proj.transform([box[2], box[3]], 'EPSG:3857', 'EPSG:4326');
            
      if(this.move_timer != false)
      {
        clearTimeout(this.move_timer);
      }
      this.move_timer = setTimeout(this.map_reload.bind( self ),3000);
      
      
    }
    
  }
  
  app.controller('indexController', function($http,$scope,$location) {
    return new indexController($http,$scope,$location);
  });
  
})();