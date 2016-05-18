'use strict';

(function() {
  
  class offlineController {
    constructor($http, $scope) {
      this.host = "";
      
      this.$scope = $scope;
      this.$http = $http;
      this.play = true;
      
      this.$scope.link_status = false;
      this.$scope.button_text = 'Pause';
      
      var self = this;
      this.$scope.play_pause = function() {
        self.play = !self.play;
        if(self.play) {
          self.$scope.button_text='Pause';
        } else {
          self.$scope.button_text='Play';
        }
        self.refresh();
      }
      
      this.$scope.select = function(id) {
        $("."+id).addClass("selected");
      }
      
      this.$scope.unselect = function(id) {
        $("."+id).removeClass("selected");
      }
      
      this.$scope.get_station_class = function(bssid) {
        return bssid.replace(/:/g, '_');
      }
      
      this.changeHost();
    }
    
    refresh() {
      if(this.play) {
        setTimeout(this.update.bind( this ),1000);
      }
    }
    
    update() {
      var self = this;
      this.$http.get(this.host+'/status.json').then(response => {
        if(!this.play) {
          return;
        }
        self.$scope.status = response.data;
        self.$scope.link_status = true;
        try {
          if(response.data['position']['wifi']['fix']) {
            self.$scope.status['position']['wifi']['accuracy'] = Math.round(self.$scope.status['position']['wifi']['accuracy']);
          }
          if(response.data['position']['gps']['fix']) {
            self.$scope.status['position']['gps']['accuracy'] = Math.round(self.$scope.status['position']['gps']['accuracy']);
          }
        
          this.$scope.labels_stations = [];
          this.$scope.data_stations = [];
          
          for(var i in response.data['current']['stations']) {
            var labels = [];
            var data = [[]];
            for(var j in response.data['current']['stations'][i]['history']) {
              var day = response.data['current']['stations'][i]['history'][j];
              labels.push(day[1]);
              data[0].push(day[2]);
            }
            this.$scope.labels_stations.push(labels);
            this.$scope.data_stations.push(data);
          }
          
          
          this.$scope.labels_bt_stations = [];
          this.$scope.data_bt_stations = [];
          
          for(var i in response.data['current']['bluetooth']) {
            var labels = [];
            var data = [[]];
            for(var j in response.data['current']['bluetooth'][i]['history']) {
              var day = response.data['current']['bluetooth'][i]['history'][j];
              labels.push(day[1]);
              data[0].push(day[2]);
            }
            this.$scope.labels_bt_stations.push(labels);
            this.$scope.data_bt_stations.push(data);
          }
        } catch(e) {
          console.log(e);
        }
        
        self.refresh();
      }, function errorCallback(response) {
        self.$scope.link_status = false;
        self.$scope.status = {};
        self.refresh();
      });
    }
    
    changeHost() {
      this.update();
    }
  }
  
  app.controller('offlineController', function($http,$scope) {
    return new offlineController($http,$scope);
  });
  
})();