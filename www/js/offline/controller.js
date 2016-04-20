'use strict';

(function() {
  
  class offlineController {
    constructor($http, $scope) {
      this.host = "";
      
      this.$scope = $scope;
      this.$http = $http;
      this.play = true;
      
      this.$scope.link_status = false;
      
      var self = this;
      this.$scope.play_pause = function() {
        self.play = !self.play;
        self.refresh();
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
        self.$scope.status = response.data;
        self.$scope.link_status = true;
        if(response.data['position']['wifi']['fix']) {
          self.$scope.status['position']['wifi']['accuracy'] = Math.round(self.$scope.status['position']['wifi']['accuracy']);
        }
        if(response.data['position']['gps']['fix']) {
          self.$scope.status['position']['gps']['accuracy'] = Math.round(self.$scope.status['position']['gps']['accuracy']);
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