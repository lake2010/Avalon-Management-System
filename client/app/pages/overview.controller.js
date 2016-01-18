(function() {
	'use strict';

	angular
		.module('ams')
		.controller('OverviewController', OverviewController);

	OverviewController.$inject = ['ShareService', 'APIService'];

	function OverviewController(share, api) {
		/* jshint validthis: true */
		var vm = this;

		vm.status = share.status.overview;

		share.status.main.title = "Overview";
		share.status.main.subTitle = false;

		vm.hashrateChart = {};
		vm.hashrateChart.loaded = false;
		vm.hashrateChart.options = share.hashrateChartOptions;
		vm.aliverateChart = {};
		vm.aliverateChart.loaded = false;
		vm.aliverateChart.options = share.aliverateChartOptions;
		vm.summaryLoaded = false;
		vm.data = api.data;

		vm.summaryTable = [{
			name: 'Node',
			value: function(data) {return data.ip + ':' + data.port;},
		}, {
			name: 'Modules',
			value: function(data) {return data.module;},
		}, {
			name: 'Temperature',
			value: function(data) {
				return parseFloat(data.temp).toFixed(1) +
					' / ' + parseFloat(data.temp0).toFixed(1) +
					' / ' + parseFloat(data.temp1).toFixed(1);
			},
		}];

		if (share.status.main.time === 0)
			share.getLastTime().then(getChart);
		else
			getChart();

		function getChart() {
			api.getFarmHashrate(
				share.status.main.time - 30 * 24 * 3600,
				share.status.main.time
			).then(
				function() {
					vm.hashrateChart.loaded = true;
			});

			api.getSummary(share.status.main.time).then(
				function() {
					vm.summaryLoaded = true;
			});

			api.getAliverate(
				share.status.main.time - 30 * 24 * 3600,
				share.status.main.time
			).then(
				function() {
					vm.aliverateChart.loaded = true;
			});
		}
	}
})();
