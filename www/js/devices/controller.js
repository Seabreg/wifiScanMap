'use strict';

(function() {
  
  class devicesController {
    constructor($http, $scope, $location) {
      this.host = "";
      this.$location = $location
      
      this.$scope = $scope;
      this.$scope.link_status = false;
      this.$http = $http;


      this.devicesSource = new ol.source.Vector({});
      
      this.map = new ol.Map({
        layers: [
        new ol.layer.Tile({
          source: new ol.source.OSM()
        }),
        new ol.layer.Vector({
          source: this.devicesSource,
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
      var self = this;
      this.map.getViewport().addEventListener('click', function (e) {
        e.preventDefault();
        
        
        var feature = self.map.forEachFeatureAtPixel(self.map.getEventPixel(e),
                                                     function (feature, layer) {
                                                       return feature;
                                                     });
        if (feature) {
          var html = "";
          var device = feature.getProperties().device;
          html += device['hostname'] + '<br/>';
          html += device['date'] + '<br/>';
          html += device['source'] + '<br/>';
          $("#left-pannel").html(html);
          $("#left-pannel").show();
        } else {
          $("#left-pannel").hide(); 
        }
      });
      
      this.changeHost();
    }


    
    update_devices() {
      $("#loading-container").show();
      this.devicesSource.clear();
      var self = this;
      this.$http.get(this.host + '/devices.json').then(response => {
        for(var i in response.data) {
          var point = new ol.geom.Point( ol.proj.transform([response.data[i]["longitude"], response.data[i]["latitude"]], 'EPSG:4326', 'EPSG:3857'));
          var device = new ol.Feature({
            geometry: point,
            device : response.data[i]
          });
          var pointStyle = new ol.style.Style({
            image: new ol.style.Circle({
              //               fill: new ol.style.Fill({
              //                 color: color
              //               }),
              stroke: new ol.style.Stroke({
                color: 'blue',
                width: 2
              }),
              radius: 4,
            })
          })
          device.setStyle(pointStyle);
          this.map.getView().setCenter(ol.proj.transform([response.data[i]["longitude"], response.data[i]["latitude"]], 'EPSG:4326', 'EPSG:3857'));
          this.devicesSource.addFeature( device );
        }
        
        self.$scope.link_status = true;
        setTimeout(self.update_devices.bind( self ),10000);
        
        $("#loading-container").hide();
      }, function errorCallback(response) {
        self.$scope.link_status = false;
        $("#loading-container").hide();
        setTimeout(self.update_devices.bind( self ),10000);
      });
    }
    
 
    changeHost() {
      this.update_devices();
    }
    
  }
  
  app.controller('devicesController', function($http,$scope,$location) {
    return new devicesController($http,$scope,$location);
  });
  
})();