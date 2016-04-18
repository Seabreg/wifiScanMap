'use strict';

(function() {
  
  class probesController {
    constructor($http, $scope) {
      this.host = "";
      
      this.$scope = $scope;
      this.$http = $http;
      this.changeHost();
    }
      
      
    
    update() {
      var self = this;
      this.$http.get(this.host+'/probes.json').then(response => {
        self.$scope.probes = response.data;
      }, function errorCallback(response) {
        self.$scope.link_status = false;
      });
    }
    
    changeHost() {
      this.update();
    }
  }
  
  app.controller('probesController', function($http,$scope) {
    return new probesController($http,$scope);
  });
  
})();