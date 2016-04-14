'use strict';

(function() {
  
  class offlineController {
    constructor($http, $scope) {
      this.host = "";
      
      this.$scope = $scope;
      this.$http = $http;
      this.changeHost();
    }
      
      
    
    update() {
      this.$http.get(this.host+'/status.json').then(response => {
        this.$scope.status = response.data;
        setTimeout(this.update.bind( this ),1000);
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