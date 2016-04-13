'use strict';

var taskApp = angular.module("taskApp", ['ui.bootstrap']);
taskApp.controller("taskController", function ($scope, $http, $interval, $log) {
    $scope.list = {
        items: []
    };

    $scope.options = {
        status: [
            'All',
            'Idle',
            'Running',
            'Failed',
            'Success',
            'Cancelled',
            'Pending'
        ],
        sort: [
            'Date'
        ]
    };
    ;

    $scope.defaultParams = {
        status: 'All',
        sort: 'Date',
        q: undefined,
        offset: 0,
        count: 5
    };
    ;

    $scope.formParams = angular.copy($scope.defaultParams);
    ;
    $scope.params = angular.copy($scope.defaultParams);
    ;

    $scope.search = function () {
        $scope.params = angular.copy($scope.formParams);
        ;
        $scope.update()
    };
    ;

    $scope.reset = function () {
        $scope.formParams = angular.copy($scope.defaultParams)
    };
    ;

    $scope.update = function () {
        $http({
            method: 'GET',
            url: 'http://localhost:5000/info',
            params: $scope.params
        }).then(function successCallback(response) {
            $scope.list = response.data.tasks
        }, function errorCallback(response) {
            $log.warn('error loading data')
        });
    };
    ;

    $scope.update();
    ;
    $interval($scope.update, 5000)


});
taskApp.controller("createFormController", function ($scope, $uibModal, $log) {

    $scope.items = ['item1', 'item2', 'item3'];

    $scope.open = function (size) {

        $log.info('open');

        var modalInstance = $uibModal.open({
            animation: $scope.animationsEnabled,
            templateUrl: 'partical/add-form.html',
            controller: 'modalController',
            size: size,
            resolve: {
                items: function () {
                    return $scope.items;
                }
            }
        });

        modalInstance.result.then(function (selectedItem) {
            $scope.selected = selectedItem;
        }, function () {
            $log.info('Modal dismissed at: ' + new Date());
        });
    };

    $scope.toggleAnimation = function () {
        $scope.animationsEnabled = !$scope.animationsEnabled;
    };

});


taskApp.controller('modalController', function ($scope, $uibModalInstance) {

    /*$scope.ok = function () {
     $uibModalInstance.close($scope.selected.item);
     };*/

    $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
    };
});


// Declare app level module which depends on views, and components
/*angular.module('myApp', [
 'ngRoute',
 'myApp.view1',
 'myApp.view2',
 'myApp.version'
 ]).
 config(['$routeProvider', function($routeProvider) {
 $routeProvider.otherwise({redirectTo: '/view1'});
 }]);
 */