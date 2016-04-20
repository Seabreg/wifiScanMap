'use strict';

(function() {
  
  class statsController {
    constructor($http, $scope) {
      this.host = "";
      
      this.$scope = $scope;
      this.$http = $http;
      this.changeHost();
    }
      
      
    
    update() {
      var self = this;
      this.$http.get(this.host+'/stats.json').then(response => {
        self.$scope.stats = response.data;
      }, function errorCallback(response) {
        self.$scope.link_status = false;
      });
    }
    
    changeHost() {
      this.update();
    }
  }
  
  app.controller('statsController', function($http,$scope) {
    return new statsController($http,$scope);
  });
  
})();