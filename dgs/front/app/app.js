'use strict';

var taskApp = angular.module("taskApp", ['ui.bootstrap']);
taskApp.controller("taskController", function ($scope, $http, $interval, $log) {
    $scope.list = {
        items: []
    };

    $scope.isCollapsed = {};

    $scope.options = {
        state: [
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


    $scope.defaultParams = {
        state: 'All',
        sort: 'Date',
        q: undefined,
        offset: 0,
        count: 5
    };


    $scope.formParams = angular.copy($scope.defaultParams);

    $scope.params = angular.copy($scope.defaultParams);


    $scope.search = function () {
        $scope.params = angular.copy($scope.formParams);

        $scope.update()
    };


    $scope.reset = function () {
        $scope.formParams = angular.copy($scope.defaultParams)
    };


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

    $scope.cancel = function (task_id) {
        $http({
            method: 'GET',
            url: 'http://localhost:5000/cancel/' + task_id
        }).then(function successCallback(response) {
            alert('Task cancelled!');
        }, function errorCallback(response) {
            alert('Error');
        });
    };

    $scope.canCancel = function (state) {
        return state == 'Idle' || state == 'Pending' || state == 'Running';
    };


    $scope.update();

    $interval($scope.update, 10000)


});
taskApp.controller("createFormController", function ($scope, $uibModal, $log) {

    $scope.items = ['item1', 'item2', 'item3'];

    $scope.open = function (size) {

        $log.info('open');

        var modalInstance = $uibModal.open({
            animation: $scope.animationsEnabled,
            templateUrl: 'myModalContent.html',
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

taskApp.controller('modalController', function ($scope, $uibModalInstance, $http, $log) {

    $scope.formParams = {
        title: 'Custom task',
        file: undefined
    };

    $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
    };

    $scope.onFileSelect = function ($files) {
        $scope.formParams.file = $files[0];
    };

    $scope.doAddTask = function () {
        var reader = new FileReader();
        reader.onload = function (e) {
            $http({
                method: 'POST',
                url: 'http://localhost:5000/add',
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                data: {
                    file: reader.result,
                    title: $scope.formParams.title
                }
            }).then(function successCallback(response) {
                alert("Task added!");
            }, function errorCallback(response) {
                var message = 'Adding task failed';
                for (var e in response.data.message) {
                    message += '\n' + e + ': ' + response.data.message[e].ex_message;
                }
                alert(message);
            });
        };
        reader.readAsText($scope.formParams.file)
    };

    $scope.addTask = function () {
        $log.info('Sending data...');
        $scope.doAddTask();


        $uibModalInstance.dismiss('ok');
    }
});