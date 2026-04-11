$(document).ready(function () {
// mobile js 파일 추가
	let hostname = window.location.hostname;
	let domainarr = hostname.split('.');
	if(domainarr.indexOf('m') < 0) {
		if(domainarr[0] === 'www') {
			// real
			domainarr[0] = 'm';
		} else if(domainarr.length === 2 ) {
			domainarr.splice(0, 0, 'm');
		} else if (domainarr[0] === 'stg') {
			domainarr[0] = 'stg-m';
		} else {
			if (domainarr[0] === 'dev') {
				domainarr[0] = 'dev-m';
			} else if (domainarr[0] === 'local') {
				domainarr.splice(1, 0, 'm');
			}
		}
		hostname = domainarr.join('.');

		if (domainarr[0] === 'localhost') {
			hostname = "local.m.prismlive.com";
		}
		console.log(hostname);
	}

	var js_uri = window.location.protocol + "//" + hostname + '/js/prism.js';
	console.log(js_uri);
	$('head').append('<script src="' + js_uri + '"></script>');
});
