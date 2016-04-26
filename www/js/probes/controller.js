'use strict';

(function() {
  
  class probesController {
    constructor($http, $scope, $location) {
      this.host = "";
      this.$location = $location
      this.$scope = $scope;
      this.$http = $http;
      this.$scope.terms = "";
      
      var search = this.$location.search()
      if(search.essid != undefined) {
        this.$scope.terms = search.essid;
      }
      
      this.changeHost();
    }
      
      
    
    update() {
      var self = this;
      
      var params = "";
      if(this.$scope.terms != "") {
        params = "?essid=" + this.$scope.terms;
      }
      $("#loading-container").show();
      this.$http.get(this.host+'/probes.json' + params).then(response => {
        self.$scope.probes = response.data;
        $("#loading-container").hide();
      }, function errorCallback(response) {
        $("#loading-container").hide();
        self.$scope.link_status = false;
      });
    }
    
    changeHost() {
      this.update();
    }
  }
  
  app.controller('probesController', function($http,$scope,$location) {
    return new probesController($http,$scope,$location);
  });
  
})();