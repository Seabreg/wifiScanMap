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
        
        this.$scope.essid_labels = [];
        this.$scope.essid_data = [[]];
        
        for(var i in response.data['wifis']['top']) {
          var wifi = response.data['wifis']['top'][i];
          this.$scope.essid_labels.push(wifi[0]);
          this.$scope.essid_data[0].push(wifi[1]);
        }
        
        
        this.$scope.probes_labels = [];
        this.$scope.probes_data = [[]];
        
        for(var i in response.data['probes']['top']) {
          var wifi = response.data['probes']['top'][i];
          this.$scope.probes_labels.push(wifi[0]);
          this.$scope.probes_data[0].push(wifi[1]);
        }
        
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