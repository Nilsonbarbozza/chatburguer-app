// real.js
let tokenCheckUrl = "https://apis.naver.com/prism/prism-auth-api/email/password/token";
let pwdChangeUrl = "https://apis.naver.com/prism/prism-auth-api/email/password";
let env = 'real'; // default value

// HMAC Blacklist 등록된 URI로 요청. 해외 접속을 고려하여 api gw로 요청
let latestPcClientUrl = "https://apis.naver.com/prism/prism-sync-api/pcapp/latest";
// 이전버전 제공 Url - 고정
const fallbackWin64StudioUrl = "https://resource-prismlive.pstatic.net/202306092022/PrismLiveStudio_Setup_x64_3.1.4.340.exe";
let fallbackWin64LensUrl = "https://resource-prismlive.pstatic.net/202309081049/PRISMLens_Setup_x64_1.0.4.165.exe";
let fallbackMacStudioUrl = "https://resource-prismlive.pstatic.net/202309251141/PRISMLiveStudio_macos_arm64_1.0.0.132.dmg";
// TODO 신규 앱 배포 후 반영해야 함
let fallbackMacLensUrl = "";

// SNS
const notiBlogUrlKR = " https://blog.naver.com/prismlivestudio/223120501071";
const notiBlogUrlEN = "https://medium.com/@prismliveofficial/windows-prism-lens-v1-0-0-release-eadfc69aa467";
const blogUrlKR = "https://blog.naver.com/prismlivestudio";
const blogUrlEN = "https://medium.com/prismlivestudio";
const discordUrl = "https://discord.gg/e2HsWnf48R";
const youtubeUrl = "https://www.youtube.com/@prismlivestudio";

// 기타 링크
const giphyUrl = "https://giphy.com/prismlivestudio";
const navercorpUrl = "https://www.navercorp.com/";
let facebookPrivacyUrl = "https://m.facebook.com/privacy/touch/apps/permissions/?appid=1957507177907502";


function setProfile() {
	const host = window.location.hostname;
	// profile 설정
	if (host.indexOf('local') >= 0) {
		env = 'local';
	} else if (host.indexOf('dev') >= 0) {
		env = 'dev';
	} else if (host.indexOf('stg') >= 0) {
		env = 'stg';
	}

	if (env === 'local') {
		// local.js
		tokenCheckUrl = "http://localhost:9998/email/password/token";
		pwdChangeUrl = "http://localhost:9998/email/password";

		latestPcClientUrl = "http://localhost:8880/pcapp/latest";

		facebookPrivacyUrl = "https://m.facebook.com/privacy/touch/apps/permissions/?appid=1056056317812617";

		// NTM script
		!function(t,n){n=n||"ntm";window["ntm_"+t]=n,window[n]=window[n]||[],window[n].push({"ntm.start":+new Date});t=document.getElementsByTagName("script")[0],n=document.createElement("script");n.async=!0,n.src="https://ntm-cdn.navercorp.com/scripts/ntm_3bcfd581f3cb_dev.js",t.parentNode.insertBefore(n,t)}("3bcfd581f3cb","ntm");
	} else if (env === 'dev') {
		// dev.js
		tokenCheckUrl = "/auth-api/email/password/token";
		pwdChangeUrl = "/auth-api/email/password";

		latestPcClientUrl = "/sync-api/pcapp/latest";

		facebookPrivacyUrl = "https://m.facebook.com/privacy/touch/apps/permissions/?appid=1056056317812617";

		// NTM script
		!function(t,n){n=n||"ntm";window["ntm_"+t]=n,window[n]=window[n]||[],window[n].push({"ntm.start":+new Date});t=document.getElementsByTagName("script")[0],n=document.createElement("script");n.async=!0,n.src="https://ntm-cdn.navercorp.com/scripts/ntm_3bcfd581f3cb_dev.js",t.parentNode.insertBefore(n,t)}("3bcfd581f3cb","ntm");


	} else if (env === 'stg') {
		// NTM script
		!function(t,n){n=n||"ntm";window["ntm_"+t]=n,window[n]=window[n]||[],window[n].push({"ntm.start":+new Date});t=document.getElementsByTagName("script")[0],n=document.createElement("script");n.async=!0,n.src="https://ntm.pstatic.net/scripts/ntm_3bcfd581f3cb_stage.js",t.parentNode.insertBefore(n,t)}("3bcfd581f3cb","ntm");
	} else {
		// NTM script
		!function(t,n){n=n||"ntm";window["ntm_"+t]=n,window[n]=window[n]||[],window[n].push({"ntm.start":+new Date});t=document.getElementsByTagName("script")[0],n=document.createElement("script");n.async=!0,n.src="https://ntm.pstatic.net/scripts/ntm_3bcfd581f3cb.js",t.parentNode.insertBefore(n,t)}("3bcfd581f3cb","ntm");
	}

    window.dispatchEvent(new Event('prismjs-loaded'))
	return env;
}

function geturlparameter(sParam) {
	var sPageURL = decodeURIComponent(window.location.search.substring(1)),
		sURLVariables = sPageURL.split('&'),
		sParameterName,
		i;
	for (i = 0; i < sURLVariables.length; i++) {

		sParameterName = sURLVariables[i].split('=');

		if (sParameterName[0] === sParam) {
			return sParameterName[1] === undefined ? "" : sParameterName[1];
		}
	}

	return "";
}

function sendEventLog(clickArea) {
	// NTM 에서 생성한 트리거의 이벤트 명 - pc: click-pc, mo: click-mobile
	let eventName = "click-pc";
	if (is_mobile_page()) {
		eventName = "click-mobile";
	}
	ntm.push({
		event: eventName,
		click_area: clickArea, // 미리 정의한 이벤트 영역클릭정의표 값
	});
}

function changeUrl(tab) {
	const url = new URL(window.location.href);
	const searchParams = new URLSearchParams(url.search);

	searchParams.set('app', tab);
	url.search = searchParams.toString();
	window.history.replaceState(null, null, url.href);
}

function is_mobile_page() {
	let domainArr = window.location.hostname.split('.');
	if(domainArr.indexOf('m') < 0 && domainArr.indexOf('stg-m') < 0 && domainArr.indexOf('dev-m') < 0) {
		return false;
	}
	return true;
}

(function() {
	var chrome   = navigator.userAgent.indexOf('Chrome') > -1;
	var explorer = navigator.userAgent.indexOf('MSIE') > -1;
	var firefox  = navigator.userAgent.indexOf('Firefox') > -1;
	var safari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
	var camino   = navigator.userAgent.indexOf("Camino") > -1;
	var opera    = navigator.userAgent.toLowerCase().indexOf("op") > -1;
	if ((chrome) && (safari)) safari = false;
	if ((chrome) && (opera)) chrome = false;
	if (chrome || safari) {
		var $prism_description6 = $('.prism_description6 .inner');
		$prism_description6.addClass('add_contrast');
	}
})();

function url(pathname) {
	return window.location.origin + pathname;
}

function parseLang() {
	const curPathname = window.location.pathname;
	let lang = 'en_us'; // default value
	const langRegex = /[a-zA-Z]{2}_[a-zA-Z]{2}/;

	if (langRegex.test(curPathname)) {
		lang = curPathname.match(langRegex)[0];
	}
	return lang;
}

function go_home(a) {
	if (!/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
		a.setAttribute('href', getPcUrl() + '/' + parseLang() + '/home.html');
	} else {
		a.setAttribute('href', '/' + parseLang() + '/home.html');
	}
}

function go_bridge(a) {
	let url =  '/' + parseLang() + '/bridge.html'
	if(a){
		a.setAttribute('href', url);
	}else{
		location.href = url;
	}
}

function go_navercorp(a) {
	a.setAttribute('href', navercorpUrl);
}

function go_mobile(a) {
	a.setAttribute('href', '/' + parseLang() + '/mobile.html');
}

function go_pc(a) {
	a.setAttribute('href', '/' + parseLang() + '/desktop.html');
}

function go_lens(a) {
	a.setAttribute('href', '/' + parseLang() + '/lens.html');
}
function go_effect(a) {
	a.setAttribute('href', '/' + parseLang() + '/effect.html');
}
function go_plus(a) {
	a.setAttribute('href', '/' + parseLang() + '/plus.html');
}


function prismTermsOfUseUrl() {
	if (window.PRISM_LEGAL && typeof window.PRISM_LEGAL.termsOfUseUrl === 'function') {
		return window.PRISM_LEGAL.termsOfUseUrl(parseLang());
	}
	const hash = parseLang().indexOf('ko') > -1 ? 'undefined-1' : 'en';
	return 'https://guide.prismlive.com/legal/terms-of-use#' + hash;
}

function go_term(a) {
	a.setAttribute('href', prismTermsOfUseUrl());
}

// 이용약관 추가시 아래 배열에 terms_content_ 뒤의 값을 추가해주시면 됩니다.
const terms_years = ["2021", "2022", "2025"];

function go_prev_terms(a) {
	const pathname = window.location.pathname;
	const res = pathname.split('/'); // 빈문자열, 언어, policy, terms_content[_년도].html

	let prevYear = terms_years[terms_years.length-1];
	if (res[3] !== "terms_content.html") {
		const currentYear = res[3].replace("terms_content_","").replace(".html","");
		prevYear = terms_years[terms_years.indexOf(currentYear)-1];
	}
	a.setAttribute('href', '/' + parseLang() + '/policy/terms_content_' + prevYear + '.html');

}

function prismPrivacyPolicyUrl() {
	if (window.PRISM_LEGAL && typeof window.PRISM_LEGAL.privacyPolicyUrl === 'function') {
		return window.PRISM_LEGAL.privacyPolicyUrl(parseLang());
	}
	const hash = parseLang().indexOf('ko') > -1 ? 'undefined-1' : 'en';
	return 'https://guide.prismlive.com/legal/privacy-policy#' + hash;
}

function go_privacy(a) {
	a.setAttribute('href', prismPrivacyPolicyUrl());
}

// 개인정보처리방침 추가시 아래 배열에 privacy_content_ 뒤의 값을 추가해주시면 됩니다.
const privacy_years = ["2017", "2020", "2021", "2023", "2024", "2025", "20251","20252"];
const privacy_years_kr = ["2017", "2020", "2021", "2023", "2024", "2025", "20251","20252"];

function go_prev_privacy(a) {
	const pathname = window.location.pathname;
	const res = pathname.split('/'); // 빈문자열, 언어, policy, privacy_content[_년도].html
	let lang = parseLang();
	let yearsList = parseLang().indexOf('ko')>-1?privacy_years_kr:privacy_years
	let prevYear = yearsList[yearsList.length-1];
	if (res[3] !== "privacy_content.html") {
		const currentYear = res[3].replace("privacy_content_","").replace(".html","");
		prevYear = yearsList[yearsList.indexOf(currentYear)-1];
	}
	a.setAttribute('href', '/' + parseLang() + '/policy/privacy_content_' + prevYear + '.html');
}

function go_signout(a) {
	window.open(getMoUrl() + '/' + parseLang() + '/login/login.html', "_self");
}

function app() {
	if (is_mobile_page()) {
		return 'mapp';
	} else {
		return 'pcapp';
	}
}

function go_faq(a, app) {
	a.setAttribute('href', '/' + parseLang() + '/faq/faq.html?app=' + app);
}

function select_tab(tab) {
	$('.tab-list li a').parent('li').removeClass('selectd');
	$('li[rel="'+tab+'"]').addClass('selectd');
	$('.tab-content').hide();
	$('#'+tab).fadeIn();
}

function setFaqPageTitle(tab) {
	if (!$('.prism-tab').length) return;
	var lang = parseLang();
	var titles = {
		en_us: {
			tab1: 'PRISM Mobile Help, FAQ & Troubleshooting',
			tab2: 'PRISM Desktop Help, FAQ & Troubleshooting',
			tab3: 'PRISM Lens Help, FAQ & Troubleshooting'
		},
		ko_kr: {
			tab1: 'PRISM Mobile 자주 묻는 질문 및 문제 해결 | 도움말',
			tab2: 'PRISM Desktop 자주 묻는 질문 및 문제 해결 | 도움말',
			tab3: 'PRISM Lens 자주 묻는 질문 및 문제 해결 | 도움말'
		}
	};
	var langTitles = titles[lang] || titles.en_us;
	var title = langTitles[tab];
	if (title) document.title = title;
}

function isSamsungBrowser() {
	return navigator.userAgent.match(/SamsungBrowser/i);
}

function isIE(v) {
	return RegExp('msie' + (!isNaN(v)?('\\s'+v):''), 'i').test(navigator.userAgent);
}

function getPcUrl() {
	// Use relative entry for PC; Nginx redirects /pc to the environment-specific PC host
	return '/pc';
}

function getMoUrl() {
	// Use relative entry for Mobile; Nginx redirects /mobile to the environment-specific Mobile host
	return '/mobile';
}

// 가로모드
function is_landscape() {
	// screen.orientation 은 이전 브라우저 버전에서 지원하지 않는 경우가 있음
	return is_mobile_page() && (window.innerWidth > window.innerHeight);
}

// 세로모드
function is_portrait() {
	return !is_landscape();
}
function is_inapp_browser_mode() {
	const userAgent = navigator.userAgent;
	return userAgent.indexOf("WorksMobile") >= 0 || userAgent.indexOf("NaverWorks") >= 0;
}

var isUnsupportedBrowser = (function() {
	var ans = isSamsungBrowser() || isIE(10);
	return function() {
		return ans;
	}
})();

const checkToken = function () {
	// 토큰 정보 가져오기
	const query = window.location.search.substring(1);
	const params = query.split('&');
	let token;
	params.forEach(param => {
		const paramValues = param.split("=");
		if ("tk" === paramValues[0]) {
			token = paramValues[1];
		}
	})

	$.ajax({
		url: tokenCheckUrl,
		data: {
			token: token
		},
		type: "GET",
		contentType: 'application/json',
		dataType: 'json',
		success: function (res) {
			console.log("success", res);
		},
		error: function (response, status) {
			console.log("response", response);
			console.log("status", status);
			window.open('/' + parseLang() + '/changepwd/expired.html', '_self');
		},
		timeout: 10000
	});
}

$(document).ready(function() {
	profile = setProfile();
	console.log(profile);
	var userAgent = navigator.userAgent || navigator.vendor || window.opera;

	cur_app = app();

	if (isUnsupportedBrowser()) {
		var enableReplacementVideos = document.getElementsByClassName('enableReplacement');
		$.each(enableReplacementVideos, function(idx, video) {
			var $video = $(video),
				replacementPoster = $video.data('replacementPoster');
			$video.attr('poster', replacementPoster);
			$video.removeAttr('data-replacement-poster');
		});
	}

	if (is_landscape() && is_inapp_browser_mode()) {
		$('.wrap').addClass('inapp');
	}
	// 인앱브라우저 세이프 에어리어 처리
	window.addEventListener('resize', function() {
		if (is_landscape() && is_inapp_browser_mode()) {
			$('.wrap').addClass('inapp');
		} else if (is_portrait()) {
			$('.wrap').removeClass('inapp');
		}
	});

	//// 언어 변경 ////
	$('.lang_list li').click(function () {
		const selectedLang = $(this).attr('class');
		let path = window.location.pathname;

		// faq tab 정보 추가용
		if ($('.prism-tab').length > 0) {
			const activeTab = $('.selectd').attr('rel');
			$(this).children('a')[0].setAttribute('href', path.replace(/[a-zA-Z]{2}_[a-zA-Z]{2}/, selectedLang) + "?app=" + activeTab);
		} else {
			$(this).children('a')[0].setAttribute('href', path.replace(/[a-zA-Z]{2}_[a-zA-Z]{2}/, selectedLang));
		}
	});

	// 모바일용
	$('.lang_select .select_btn').click(function () {
        $(this).toggleClass("open");
	});
	$('.lang_select .select_btn a').click(function () {
		const selectedLang = $(this).attr('class').match(/[a-zA-Z]{2}_[a-zA-Z]{2}/)[0];
		if (selectedLang !== parseLang()) {
			let path = window.location.pathname;
			// faq tab 정보 추가용
			if ($('.prism-tab').length > 0) {
				const activeTab = $('.selectd').attr('rel');
				this.setAttribute('href', path.replace(/[a-zA-Z]{2}_[a-zA-Z]{2}/, selectedLang) + "?app=" + activeTab);
				this.setAttribute('aria-selected', "true");

			} else {
				this.setAttribute('href', path.replace(/[a-zA-Z]{2}_[a-zA-Z]{2}/, selectedLang));
				this.setAttribute('aria-selected', "true");
			}
		}
	});

	$('.prism-logo, .logo, .copyright, .live, .error_logo').click(function () {
		if ($(this).is('a')) {
			go_home(this);
		} else {
			go_home($(this).children('a')[0]);
		}
	});

	$('.go-bridge').click(function () {
		if ($(this).is('a')) {
			go_bridge(this);
		} else if($(this).is('button')) {
			go_bridge();
		} else {
			go_bridge($(this).children('a')[0]);
		}
	});
	$('.copyright').click(function () {
		go_navercorp(this);
	})

	$('.mobileP').click(function () {
		go_mobile($(this).children('a')[0]);
	});
	$('.mobile-section').click(function () {
		const section = $(this).attr('id');
		$(this).children('a')[0].setAttribute('href', '/' + parseLang() + '/mobile.html#' + section);

		if (section === 'multistream') {
			sendEventLog('banner.multi');
		} else if (section === 'screencast') {
			sendEventLog('banner.screencast');
		} else if (section === 'vtuber') {
			sendEventLog('banner.vtuber');
		} else if (section === 'connect') {
			sendEventLog('banner.remote');
		}
	});
	$('.desktopP').click(function () {
		go_pc($(this).children('a')[0]);
	});
	$('.desktop-section').click(function () {
		const section = $(this).attr('id');
		$(this).children('a')[0].setAttribute('href', '/' + parseLang() + '/desktop.html#' + section);

		sendEventLog('banner.source');
	});

	$('.lensP').click(function () {
		go_lens($(this).children('a')[0]);
	});
	$('.effectP').click(function () {
		go_effect($(this).children('a')[0]);
	});
	$('.header-plus').click(function () {
		go_plus($(this).children('a')[0]);
	});
	$('.footer-plus').click(function (e) {
		go_plus($(this).children('a')[0]);
	});
	$('.footer-promo-code').click(function (e) {
		e.preventDefault();
		var isPC = window.__IS_PC_PAGE__;
		if (isPC === undefined) {
			var params = new URLSearchParams(window.location.search);
			isPC = params.get('isPC') === 'true';
		}
		var lang = parseLang();
		var loginFile = isPC ? 'pc_code_login.html' : 'code_login.html';
		window.location.href =
			'/mobile/' + lang + '/promotion_code/' + loginFile;
	});

	$('.terms, .footer_term').click(function (e) {
		window.open(prismTermsOfUseUrl(), "_blank");
	});

	$('.prev_terms').click(function () {
		go_prev_terms($(this).children('a')[0]);
	});

	$('.privacy, .footer_privacy').click(function (e) {
		window.open(prismPrivacyPolicyUrl(), "_blank");
	});

	$('.signout').click(function () {
		go_signout();
	});

	$('.prev_privacy').click(function () {
		go_prev_privacy($(this).children('a')[0]);
	});

	$('.faq, .footer_faq, .help').click(function () {
		go_faq($(this).children('a')[0], "mapp");
	});

	$('.faq-mapp').click(function () {
		go_faq($(this).children('a')[0], "mapp");
	})
	$('.faq-pcapp').click(function () {
		go_faq($(this).children('a')[0], "pcapp");
	})
	$('.faq-lens').click(function () {
		go_faq($(this).children('a')[0], "lens");
	})


	$('.prism_button_google, .google_play').click(function() {
		download('');

		return false;
	});

	$('.prism_button_ios, .app_store').click(function() {
		download('iPhone');

		return false;
	});

	$('.spot.desktop .btn_area .download_btn, .lens .download_btn').click(function () {
		let text;
		if (window.location.pathname.indexOf("lens") >= 0) {
			text = getPcUrl() + "/" + parseLang() + "/lens.html";
		} else if (window.location.pathname.indexOf("desktop") >= 0) {
			text = getPcUrl() + "/" + parseLang() + "/desktop.html";
		}

		// 가상 텍스트 영역 생성
		let tempInput = $("<input>");
		$("body").append(tempInput);
		tempInput.val(text).select();

		// 복사 명령 실행
		document.execCommand("copy");

		// 가상 텍스트 영역 제거
		tempInput.remove();
		sendEventLog('download');
	});

	$('.download, .mobile .download_btn, .home .download_btn').click(function() {
		if (is_mobile_page()) {
			download(userAgent);
			sendEventLog('download');
		}
		return false;
	});

	function download(userAgent) {
		if (/android/i.test(userAgent)) {
			window.open("market://details?id=com.prism.live", "_self");
		} else if (/iPad|iPhone|iPod/.test(userAgent)) {
			if(is_mobile_page()) {
				window.open("itms-apps://itunes.apple.com/app/id1319056339", "_self");
			} else {
				window.open("https://itunes.apple.com/app/id1319056339", "_blank");
			}
		} else {
			window.open("https://play.google.com/store/apps/details?id=com.prism.live", "_blank");
		}
	}

	const getPcClientUri = function(requestUri, fallbackUri, platformType, appType) {
		$.ajax({
			url: requestUri + "?platformType=" + platformType + "&appType=" + appType,
			type: "GET",
			dataType: "json",
			success: function(res) {
				window.open(res.clientUri, "_self");
			},
			error: function() {
				// TODO: 혹시 모를 error 상황에 대해서 구 버전의 fallback static 설정. 다른 웹 배포가 존재할 때마다 가끔 변경하자. sync가 아예 죽을 일은 없겠지만.
				window.open(fallbackUri, "_self");
			},
			timeout: 10000
		});
	}

	// download
	$('.win64_studio').click(function() {
		console.log("download");
		getPcClientUri(latestPcClientUrl, fallbackWin64StudioUrl, "WIN64", "LIVE_STUDIO");
		return false;
	});
	$('.mac_studio').click(function() {
		getPcClientUri(latestPcClientUrl, fallbackMacStudioUrl, "MAC", "LIVE_STUDIO");
		return false;
	});
	$('.win64_lens').click(function() {
		getPcClientUri(latestPcClientUrl, fallbackWin64LensUrl, "WIN64", "LENS");
		return false;
	});
	$('.mac_lens').click(function() {
		getPcClientUri(latestPcClientUrl, fallbackMacLensUrl, "MAC", "LENS");
		return false;
	});
	$('.origin_download').click(function() {
		window.open(fallbackWin64StudioUrl, "_self");
		sendEventLog('download.oldversion');
		return false;
	});

	$('.contact').click(function() {
		return false;
	});

	$.fn.goTo = function() {
		$('html, body').animate({
			scrollTop: $(this).offset().top + 'px'
		}, 'smooth');
		return this; // for chaining...
	}

	$.fn.goTo_gnb = function () {
		$('html, body').animate({
			scrollTop: $(this).offset().top - $('.header').height() + 'px'
		}, 'smooth');
		return this; // for chaining...
	};

	// blog noti
	$('#blog_noti_en').click(function () {
		window.open(notiBlogUrlEN, "_blank");
		return false;
	})
	$('#blog_noti_kr').click(function () {
		window.open(notiBlogUrlKR, "_blank");
		return false;
	})

	// SNS
	$('.blog_kr').click(function () {
		window.open(blogUrlKR, "_blank");
		return false;
	})
	$('.blog_en').click(function () {
		window.open(blogUrlEN, "_blank");
		return false;
	})
	$('.discord').click(function () {
		window.open(discordUrl, "_blank");
		return false;
	})
	$('.user-guide').click(function () {
		window.open('https://guide.prismlive.com', "_blank");
		return false;
	})
	$('.youtube').click(function () {
		window.open(youtubeUrl, "_blank");
		return false;
	})

	$('.giphy').click(function () {
		window.open(giphyUrl, "_blank");
		return false;
	})

	// $('.banner_area').click(function () {
	// 	$(this).attr('href', '/' + parseLang() + '/desktop.html');
	// })

	$('.faq-link, .faq-table-link, .prism_service_link').click(function() {
		if ($(this).hasClass('rtmp')) {
			select_tab('tab1');
			$('#rtmp').removeClass('hide').addClass('active').goTo_gnb();
			return false;
		} else if($(this).hasClass('vlive')) {
			select_tab('tab1');
			$('#vlive').removeClass('hide').addClass('active').goTo_gnb();
			return false;
		} else if($(this).hasClass('screencast')) {
			select_tab('tab1');
			$('#screencast').removeClass('hide').addClass('active').goTo_gnb();
			return false;
		} else if($(this).hasClass('my')) {
			select_tab('tab1');
			$('#my').removeClass('hide').addClass('active').goTo_gnb();
			return false;
		} else if ($(this).hasClass('faq-section')) {
			const section = $(this).attr('id');
			$(this).attr('href', '/' + parseLang() + '/faq/faq.html?app=mapp#' + section);
		} else {
			if($(this).hasClass('youtube')) {
				window.open("https://www.youtube.com/live_dashboard", "_blank");
			} else if($(this).hasClass('facebook')) {
				window.open("https://www.facebook.com/", "_blank");
			} else if($(this).hasClass('twitch')) {
				window.open("https://www.twitch.tv/dashboard/settings", "_blank");
			} else if($(this).hasClass('navertv')) {
				window.open("https://studio.tv.naver.com/live", "_blank");
			} else if($(this).hasClass('band')) {
				window.open("https://www.band.us", "_blank");
			} else if($(this).hasClass('afreecatv')) {
				window.open("http://dashboard.afreecatv.com/ ", "_blank");
			} else if($(this).hasClass('facebookprivacy')) {
				window.open("https://m.facebook.com/privacy/content/selector/?content_fbid=114457139315475&app_id=1056056317812617&cancel_uri=/privacy", "_blank");
			} else if($(this).hasClass('kakaotv')) {
				window.open("https://tv.kakao.com/studio/live/start ", "_blank");
			} else if($(this).hasClass('youtube_tos')) {
				window.open("https://www.youtube.com/t/terms", "_blank");
			} else if($(this).hasClass('google_privacy_policy')) {
				window.open("https://www.google.com/policies/privacy", "_blank");
			} else if ($(this).is('a')) {
				if ($(this).attr('href').indexOf('prismlive@navercorp.com') >= 0) {
					window.location.href = $(this).attr('href');
				} else if ($(this).attr('href') !== '#') {
					window.open($(this).attr('href'), "_blank");
				}
			}
			return false;
		}
	});

	$('.faq-select').click(function() {
		$(this).parent('.faq-tit').toggleClass('hide');
		return false;
	});

	$('.faq-container').click(function() {
		var $this = $(this);
		$this.parent('.faq-wrapper').toggleClass('active');
		return false;
	});

	$('.select_mask, .select_bg, .select_touch, .select_mood').click(function() {
		$('.prism_description6').removeClass('mask');
		$('.prism_description6').removeClass('background');
		$('.prism_description6').removeClass('touch');
		$('.prism_description6').removeClass('mood');

		switch($(this)[0].className) {
			case 'select_mask':
				$('.prism_description6').addClass('mask');
				break;

			case 'select_bg':
				$('.prism_description6').addClass('background');
				break;

			case 'select_touch':
				$('.prism_description6').addClass('touch');
				break;

			case 'select_mood':
				$('.prism_description6').addClass('mood');
				break;
		}

		return false;
	});

	$('.tab-mask, .tab-bg, .tab-touch, .tab-mood').click(function() {
		$('.tab-mask, .tab-bg, .tab-touch, .tab-mood').removeClass('on');
		$('.effect-content.mask, .effect-content.bg, .effect-content.touch, .effect-content.mood').removeClass('on');

		switch($(this)[0].className) {
			case 'tab-mask':
				$('.tab-mask, .effect-content.mask').addClass('on');
				break;

			case 'tab-bg':
				$('.tab-bg, .effect-content.bg').addClass('on');
				break;

			case 'tab-touch':
				$('.tab-touch, .effect-content.touch').addClass('on');
				break;

			case 'tab-mood':
				$('.tab-mood, .effect-content.mood').addClass('on');
				break;
		}

		return false;
	});

	$('.language-area').click(function() {
		if($(this).hasClass('active')) {
			$(this).removeClass('active');
		} else {
			$(this).addClass('active');
			return false;
		}
	});

	$('.prism-top, .btn_top').click(function() {
		$('html, body').animate({
			scrollTop: 0,
		}, 'slow');
		return false;
	});

	$(document).click(function(e){
		if($(e.target).hasClass('language-area')) return;
		$('.language-area').removeClass('active');
	});

	$('.comingsoon').click(function() {
		return false;
	});

	//// faq tab 선택 ////
	// 주소로 faq tab 확인
	if($('.prism-tab').length > 0) {
		const app = geturlparameter('app');
		let activeTab = 'tab1';
		if(app === 'mapp') {
			select_tab('tab1');
			activeTab = 'tab1';
		} else if (app === 'pcapp') {
			select_tab('tab2');
			activeTab = 'tab2';
		} else if (app === 'lens') {
			select_tab('tab3');
			activeTab = 'tab3';
		} else if (app === 'tab1' || app === 'tab2' || app === 'tab3') {
			select_tab(app);
			activeTab = app;
		}
		setFaqPageTitle(activeTab);
	}

	// 주소로 section 이동
	if ($('.faq, .prism-help').length > 0 ) {
		const section = window.location.hash;
		if (section) {
			$(section).removeClass('hide').addClass('active').goTo_gnb();
		}
		const link = geturlparameter('link');
		if (link) {
			const linkSelect = $('#' + link);
			if (linkSelect.length > 0) {
				linkSelect.removeClass('hide').addClass('active').goTo_gnb();
			}
		}
	}

	// faq tab 변경
	$('.tab-list li a').click(function () {
		const activeTab = $(this).parent('li').attr('rel');
		select_tab(activeTab);
		setFaqPageTitle(activeTab);
		// 주소자체가 변경되도록 수정 필요?
		changeUrl(activeTab);

		if (activeTab === 'tab1') {
			sendEventLog('tab.mobile');
		} else if (activeTab === 'tab2') {
			sendEventLog('tab.pc');
		} else if (activeTab === 'tab3') {
			sendEventLog('tab.lens');
		}
	});

	// 바로가기
	var link = geturlparameter('link');
	if(link != '' && $('#' + link).length > 0) {
		$('#' + link).removeClass('hide').addClass('active').goTo();
	}

	//// 비밀번호 변경하기 ////
	// 페이지 노출 전 토큰 만료 검사
	if (window.location.pathname.includes("/changepwd/index.html")) {checkToken();}

	const newPwd = $('#input-pw');
	const pwdCheck = $('#input-pw-re');
	const conditionText = $('.condition-text'); // 비밀번호 규칙
	const pwdUsedInfo = $('#used-before'); // 최근 사용한 비밀번호 안내
	const pwdSameInfo = $('#pw-check'); // 비밀번호 일치 여부
	const pwdResetButton = $('.btn-reset');
	const pwBox = $('.pw-box');
	const iconView = $('.icon-view');

	// 비밀번호 보이기/숨기기
	iconView.click(function(){
		pwBox.toggleClass('active');
		if(pwBox.hasClass('active')){
			iconView.prev('input').attr('type','text');
		}else{
			iconView.prev('input').attr('type','password');
		}
	});

	newPwd.keyup(function () {
		limitMaxLength(newPwd);
		togglePwdRuleInfo();
		togglePwdSameInfo();
		checkRuleAndEnableButton();
		togglePwdUsedInfo(false);
	});
	pwdCheck.keyup(function () {
		limitMaxLength(pwdCheck);
		togglePwdRuleInfo();
		togglePwdSameInfo();
		checkRuleAndEnableButton();
		togglePwdUsedInfo(false);
	})

	const limitMaxLength = function (input) {
		const maxLength = 20;
		if (input.val().length > maxLength) {
			input.val(input.val().substring(0, maxLength));
		}
	}

	const togglePwdRuleInfo = function () {
		if (newPwd.val().length && isValidPwd(newPwd.val())) {
			conditionText.addClass('check');
			conditionText.removeClass('red');
		} else if (!newPwd.val().length) {
			conditionText.removeClass('check');
			conditionText.removeClass('red');
		} else {
			conditionText.removeClass('check');
			conditionText.addClass('red');
		}
	};
	const togglePwdSameInfo = function () {
		if (!pwdCheck.val().length || isConfirmSame(newPwd.val(), pwdCheck.val())) { // 아직 입력하지 않았거나, 일치할 때
			pwdSameInfo.css('visibility', 'hidden');
		} else {
			pwdSameInfo.css('visibility', 'visible');
		}
	};
	const togglePwdUsedInfo = function (used) {
		if (used) {
			pwdUsedInfo.css('display', 'block');
			conditionText.css('display', 'none');
		} else {
			pwdUsedInfo.css('display', 'none');
			conditionText.css('display', 'block');
		}
	};

	const isValidPwd = function (pwd) {
		return pwd.match(/((?=.*\d)(?=.*[a-z,A-Z])(?=.*[_\-?/!@#$%^&*()+=,.`\[\]{}<>:;'"~\\]).{8,20})/) && pwd.length >= 8 && pwd.length <= 20;
	}
	const isConfirmSame = function (pwd1, pwd2) {
		return pwd1 === pwd2;
	};
	const isSubmitOk = function (pwd1, pwd2) {
		return isValidPwd(pwd1) && isValidPwd(pwd2) && isConfirmSame(pwd1, pwd2);
	};

	const checkRuleAndEnableButton = function () {
		if (isSubmitOk(newPwd.val(), pwdCheck.val())) {
			pwdResetButton.addClass('active');
			pwdResetButton.attr('disabled', false);
		} else {
			pwdResetButton.removeClass('active');
			pwdResetButton.attr('disabled', true);
		}
	};

	pwdResetButton.click(function () {
		if (isSubmitOk(newPwd.val(), pwdCheck.val())) {
			const data = {};
			data.password = newPwd.val();
			changePassword(data);
		}
		return false;
	});

	const changePassword = function (data) {
		// 토큰 정보 가져오기
		const query = window.location.search.substring(1);
		const params = query.split('&');
		let token;
		params.forEach(param => {
			const paramValues = param.split("=");
			if ("tk" === paramValues[0]) {
				token = paramValues[1];
			}
		})
		data.token = token;
		data.ln = parseLang();

		$.ajax({
			url: pwdChangeUrl,
			data: JSON.stringify(data),
			type: "PUT",
			contentType: 'application/json',
			dataType: 'json',
			success: function (res) {
				window.open('/' + parseLang() + '/changepwd/success.html', '_self');
			},
			error: function (response, status) {
				console.log("response", response);
				console.log("status", status);
				// if (0 === response.status) { // 로컬 테스트용
				if (400 === response.status && 11 === response.responseJSON.errorCode) {
					alreadyUsedPwd();
					return;
				}
				window.open('/' + parseLang() + '/changepwd/expired.html', '_self');
			},
			timeout: 10000
		});
	}

	const alreadyUsedPwd = function () {
		newPwd.val("");
		pwdCheck.val("");
		togglePwdRuleInfo();
		togglePwdSameInfo();
		togglePwdUsedInfo(true);
		checkRuleAndEnableButton();
	};

	// 모바일 질문
	if (is_mobile_page()) {
		$('.footer .lang_select_wrap').click(function() {
			$(this).toggleClass('open');
		});
		// 모바일 gnb
		$('.gnb_btn').click(function() {
			$( '.gnb_wrap' ).css('display' , 'block');
			$("body").css("overflow", "hidden");
			sendEventLog('gnb.menu');
		});

		$('.gnb_wrap .close').click(function() {
			$( '.gnb_wrap' ).css('display' , 'none');
			$("body").css("overflow", "auto");
			sendEventLog('gnb.close');
		});

		$('.gnb_wrap .lang_select').click(function() {
			$(this).toggleClass('open');
		});

		$(document).ready(function () {
			$(".gnb_wrap .menu_list li").click(function () {
				$(".menu_list li").not($(this)).removeClass("open");
				$(this).toggleClass("open");
				$(this).siblings('.submenu_area').css('display' , 'block');
			});
		});

		$('.question_area').click(function() {
			$(this).parent('li').toggleClass('open');
		});

		// 모바일 footer 메뉴
		$(document).ready(function () {
			$('.footer .menu_list .menu .title_area').click(function () {
				$(".menu").not($(this).parent()).removeClass("open");
				$(this).parent('.menu').toggleClass("open");
			});
		});
	}

	// NLOG 용
	/// 공통
	$('.header').click(function () {
		sendEventLog('gnb');
	})
	$('.header .logo').click(function () {
		sendEventLog('gnb.logo');
	});
	$('.title1, #product').click(function () {
		sendEventLog('gnb.product');
	});
	$('.header .effectP, .gnb_wrap .effectP').click(function () {
		sendEventLog('gnb.effect');
	});
	$('.title3, #community').click(function () {
		sendEventLog('gnb.community');
	});
	$('.gnb .mobileP').click(function () {
		sendEventLog('gnb.mobile');
	});
	$('.gnb .desktopP').click(function () {
		sendEventLog('gnb.pc');
	});
	$('.gnb .lensP').click(function () {
		sendEventLog('gnb.lens');
	});
	$('.gnb .blog_kr, .gnb .blog_en').click(function () {
		sendEventLog('gnb.blog');
	});
	$('.gnb .discord').click(function () {
		sendEventLog('gnb.discord');
	});
	$('.gnb .youtube').click(function () {
		sendEventLog('gnb.youtube');
	});
	$('.header .download_btn').click(function () {
		sendEventLog('gnb.download');
	});
	$('.header .win64_studio').click(function () {
		sendEventLog('gnb.window');
	});
	$('.header .mac_studio').click(function () {
		sendEventLog('gnb.mac');
	});
	$('.btn_area .win64_studio').click(function () {
		sendEventLog('download.window');
	});
	$('.btn_area .mac_studio').click(function () {
		sendEventLog('download.mac');
	});
	$('.footer .mobileP').click(function () {
		sendEventLog('footer.mobile');
	});
	$('.footer .desktopP').click(function () {
		sendEventLog('footer.pc');
	});
	$('.footer .lensP').click(function () {
		sendEventLog('footer.lens');
	});
	$('.footer .effectP').click(function () {
		sendEventLog('footer.effect');
	});
	$('.footer .giphy').click(function () {
		sendEventLog('footer.giphy');
	});
	$('.footer .blog_kr, .footer .blog_en').click(function () {
		sendEventLog('footer.blog');
	});
	$('.footer_menu .discord, .footer .menu .discord').click(function () {
		sendEventLog('footer.discord');
	});
	$('.footer_menu .youtube, .footer .menu .youtube').click(function () {
		sendEventLog('footer.youtube');
	});
	$('.footer .faq-mapp').click(function () {
		sendEventLog('footer.mobilefaq');
	});
	$('.footer .faq-pcapp').click(function () {
		sendEventLog('footer.pcfaq');
	});
	$('.footer .faq-lens').click(function () {
		sendEventLog('footer.lensfaq');
	});
	$('.footer .terms').click(function () {
		sendEventLog('footer.terms');
	});
	$('.footer .privacy').click(function () {
		sendEventLog('footer.pp');
	});
	$('.footer .ko_kr').click(function () {
		sendEventLog('footer.ko');
	});
	$('.footer .en_us').click(function () {
		sendEventLog('footer.en');
	});
	$('.sns .youtube').click(function () {
		sendEventLog('icon.youtube');
	});
	$('.sns .discord').click(function () {
		sendEventLog('icon.discord');
	});
	$('.top_btn').click(function () {
		sendEventLog('gototop');
	});

	/// home
	$('.banner_area .inner').click(function () {
		sendEventLog('topbanner');
	})
	$('.product .mobileP').click(function () {
		sendEventLog('link.mobilemain');
	});
	$('.product .desktopP').click(function () {
		sendEventLog('link.pcmain');
	});
	$('.product .lensP').click(function () {
		sendEventLog('link.lensmain');
	});
	$('#news1').click(function () {
		sendEventLog('news.item1');
	});
	$('#news2').click(function () {
		sendEventLog('news.item2');
	});
	$('#news3').click(function () {
		sendEventLog('news.item3');
	});
	$('.user_profile').click(function () {
		sendEventLog('recommand');
	});

	/// mobile
	$('.google_play').click(function () {
		sendEventLog('download.googleplay');
	});
	$('.app_store').click(function () {
		sendEventLog('download.appstore');
	});
	$('.effectP .more_btn').click(function () {
		sendEventLog('slot2.gotoeffect');
	});
	$('#faq1').click(function () {
		sendEventLog('faq.item1');
	});
	$('#faq2').click(function () {
		sendEventLog('faq.item2');
	});
	$('#faq3').click(function () {
		sendEventLog('faq.item3');
	});
	$('#faq4').click(function () {
		sendEventLog('faq.item4');
	});
	$('#faq5').click(function () {
		sendEventLog('faq.item5');
	});
	$('#slick-slide-control00').click(function () {
		sendEventLog('slot.item1');
	});
	$('#slick-slide-control01').click(function () {
		sendEventLog('slot.item2');
	});
	$('#slick-slide-control02').click(function () {
		sendEventLog('slot.item3');
	});

	/// terms_content
	$('.menu .terms').click(function () {
		sendEventLog('top.terms');
	});
	$('.menu .privacy').click(function () {
		sendEventLog('top.pp');
	});
	$('.menu .faq').click(function () {
		sendEventLog('top.help');
	});

	/// faq
	$('#tab1 .faq-container').click(function () {
		const title = $(this).parent().siblings(".faq-title").attr('id');
		const index = $(this).closest('.faq-wrapper').index();

		if (title === 'faq') {
			sendEventLog(title + '.item' + padTwoDigits(index));
		} else {
			sendEventLog('help.' + title + padTwoDigits(index));
		}
	});

	// mo
	/// 공통
	$('.gnb_wrap .ko_kr').click(function () {
		sendEventLog('gnb.ko');
	});
	$('.gnb_wrap .en_us').click(function () {
		sendEventLog('gnb.en');
	});
	$('#tab1 .faq-select').click(function () {
		const title = $(this).parent().parent().siblings('h2').attr('id');
		const index = $(this).closest('.faq-tit').index() + 1;

		if (title === 'faq') {
			sendEventLog(title + '.item' + padTwoDigits(index));
		} else {
			sendEventLog('help.' + title + padTwoDigits(index));
		}
	});

	function padTwoDigits(number) {
		var str = number.toString();

		if (str.length === 1) {
			str = '0' + str;
		}

		return str;
	}
});
