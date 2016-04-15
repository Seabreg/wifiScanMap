'use strict';

(function() {
  
  class offlineController {
    constructor($http, $scope) {
      this.host = "";
      
      this.$scope = $scope;
      this.$http = $http;
      this.$scope.link_status = false;
      this.changeHost();
    }
      
      
    
    update() {
      var self = this;
      this.$http.get(this.host+'/status.json').then(response => {
        self.$scope.status = response.data;
        self.$scope.link_status = true;
        setTimeout(self.update.bind( self ),1000);
      }, function errorCallback(response) {
        self.$scope.link_status = false;
        self.$scope.status = {};
        setTimeout(self.update.bind( self ),1000);
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