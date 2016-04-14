'use strict';

(function() {
  
  class indexController {
    constructor($http, $scope) {
      this.host = "";
      
      this.$scope = $scope;
      this.$http = $http;
      
      this.vectorSource = new ol.source.Vector({});
      this.map = new ol.Map({
        layers: [
        new ol.layer.Tile({
          source: new ol.source.OSM()
        }),
        new ol.layer.Vector({
          source: this.vectorSource
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
      
      this.vectorSource.addFeature( this.gps );
      this.vectorSource.addFeature( this.wifi );
      
      
      
      
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
          var wifis = feature.getProperties().wifis;
          var html = "";
          for(var i in wifis) {
            var encryption = "secure";
            if(wifis[i]["encryption"] == 0) {
              encryption = "open";
            }
            html += "<li class="+encryption+" >"+ wifis[i]["essid"] +"</li>";
          }
          $("#wifis-list").html(html);
          $("#left-pannel").show();
        } else {
          $("#left-pannel").hide(); 
        }
      });
      
      this.changeHost();
      
      
    }
    
    update() {
      this.$http.get(this.host+'/status.json').then(response => {
        this.$scope.status = response.data;
        
        if(response.data['position']['wifi']['fix']) {
          var longitude = response.data['position']['wifi']['longitude'];
          var latitude = response.data['position']['wifi']['latitude'];
          var point = new ol.geom.Point( ol.proj.transform([longitude, latitude ], 'EPSG:4326', 'EPSG:3857'));
          this.wifi.setGeometry(point);
        }
        
        if(response.data['position']['gps']['fix']) {
          var longitude = response.data['position']['gps']['longitude'];
          var latitude = response.data['position']['gps']['latitude'];
          var point = new ol.geom.Point( ol.proj.transform([longitude, latitude ], 'EPSG:4326', 'EPSG:3857'));
          this.gps.setGeometry(point);
        }
        setTimeout(this.update.bind( this ),1000);
      });
    }
    
    changeHost() {
      var wifis = [];
      var lastLat = -1;
      var lastLon = -1;
      var info = []
      this.vectorSource.clear();
      this.$http.get(this.host+'/wifis.json').then(response => {
        this.wifis_count = response.data
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
            geometry: point
          });
          wifi.setStyle(pointStyle);
          this.vectorSource.addFeature( wifi );
        }
      });
      this.update();
    }
  }
  
  app.controller('indexController', function($http,$scope) {
    return new indexController($http,$scope);
  });
  
})();