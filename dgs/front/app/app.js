'use strict';

var taskApp = angular.module('taskApp', ['ui.bootstrap', 'ngRoute']);

taskApp.config(['$routeProvider', function ($routeProvider) {
    $routeProvider.when('/tasks', {
        templateUrl: 'partial/tasks/tasks.html',
        controller: 'taskController'
    }).when('/resources', {
        templateUrl: 'partial/resources/resources.html',
        controller: 'resourceController'
    }).otherwise({
        redirectTo: '/tasks'
    });
}]);

taskApp.controller('navbarController', function ($scope, $location) {

    $scope.isActive = function (viewLocation) {
        return viewLocation === $location.path();
    };

});

taskApp.controller('taskController', function ($scope, $http, $interval, $log) {
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
            url: 'http://localhost:5000/task_info',
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
        return state == 'IDLE' || state == 'PENDING' || state == 'RUNNING';
    };


    $scope.update();

    $interval($scope.update, 10000)


});

taskApp.controller("resourceController", function ($scope, $http, $interval, $log) {
    $scope.resource_list = {
        items: []
    };

    $scope.options = {
        is_locked: [
            'all',
            true,
            false,
        ]
    };

    $scope.isCollapsed = {};

    $scope.defaultParams = {
        is_locked: 'all',
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
            url: 'http://localhost:5000/resource_info',
            params: $scope.params
        }).then(function successCallback(response) {
            $scope.resource_list = response.data.resources
        }, function errorCallback(response) {
            $log.warn('error loading data')
        });
    };


    $scope.update();

    $interval($scope.update, 10000)
});


taskApp.controller("createFormController", function ($scope, $uibModal, $log) {

    $scope.items = ['item1', 'item2', 'item3'];

    $scope.openAddTaskForm = function (size) {

        $log.info('open task form');

        var modalInstance = $uibModal.open({
            animation: $scope.animationsEnabled,
            templateUrl: 'addTaskForm.html',
            controller: 'addTaskController',
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

    $scope.openAddRecourceForm = function (size) {

        $log.info('open recourse form');

        var modalInstance = $uibModal.open({
            animation: $scope.animationsEnabled,
            templateUrl: 'addResourceForm.html',
            controller: 'addResourceController',
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

taskApp.controller('addTaskController', function ($scope, $uibModalInstance, $http, $log) {

    $scope.formParams = {
        title: '',
        file: undefined,
        resources: []
    };

    $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
    };

    $scope.onFileSelect = function ($files) {
        $scope.formParams.file = $files[0];
    };

    $scope.addNewChoice = function () {
        $scope.formParams.resources.push({});
    };

    $scope.removeChoice = function (item) {
        var index = $scope.formParams.resources.indexOf(item);
        if (index > -1) {
            $scope.formParams.resources.splice(index, 1);
        }
    };

    $scope.makeDict = function (items) {
        var result = {};
        for (var index in items) {
            var item = items[index];
            result[item.alias] = item.id
        }
        return result;
    };

    $scope.fix_resorfses_aliases = function () {
        for (var index in $scope.formParams.resources) {
            var item = $scope.formParams.resources[index];
            if (!item.alias) {
                item.alias = item.id
            }
        }
    };

    $scope.doAddTask = function () {
        $scope.fix_resorfses_aliases();
        var reader = new FileReader();
        reader.onload = function (e) {
            $http({
                method: 'POST',
                url: 'http://localhost:5000/add_task',
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                data: {
                    file: reader.result,
                    title: $scope.formParams.title,
                    resources: $scope.makeDict($scope.formParams.resources)
                }
            }).then(function successCallback(response) {
                alert('Task added!');
            }, function errorCallback(response) {
                var message = 'Adding task failed';
                if (typeof(response.data.message) === 'string') {
                    message += '\n' + response.data.message;
                } else {
                    for (var e in response.data.message) {
                        message += '\n' + e + ': ' + response.data.message[e].ex_message;
                    }
                }
                alert(message);
            });
        };
        reader.readAsText($scope.formParams.file, 'utf-8'); // input file must be in utf-8
    };

    $scope.addTask = function () {
        $log.info('Sending data...');
        $scope.doAddTask();

        $uibModalInstance.dismiss('ok');
    }
});

taskApp.controller('addResourceController', function ($scope, $uibModalInstance, $http, $log) {

    $scope.formParams = {
        title: '',
        file: undefined
    };

    $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
    };

    $scope.onFileSelect = function ($files) {
        $scope.formParams.file = $files[0];
    };

    $scope.doAddResource = function () {
        var reader = new FileReader();
        reader.onload = function (e) {
            $http({
                method: 'POST',
                url: 'http://localhost:5000/add_resource',
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                data: {
                    file: reader.result,
                    title: $scope.formParams.title
                }
            }).then(function successCallback(response) {
                alert('Resource added!');
            }, function errorCallback(response) {
                var message = 'Adding resource failed';
                if (typeof(response.data.message) === 'string') {
                    message += '\n' + response.data.message;
                } else {
                    for (var e in response.data.message) {
                        message += '\n' + e + ': ' + response.data.message[e].ex_message;
                    }
                }
                alert(message);
            });
        };
        reader.readAsText($scope.formParams.file, 'utf-8');
    };

    $scope.addResource = function () {
        $log.info('Sending data...');
        $scope.doAddResource();

        $uibModalInstance.dismiss('ok');
    }
});