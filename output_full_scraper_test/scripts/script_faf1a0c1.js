let proxyApiOrigin = "https://m.prismlive.com";
let syncApiPath = "/sync-api";
let newsApiUrl = "";
let effectsApiUlr = "";
let bannerApiUrl = "";
let maxSendTimes = 3;

function assemblyProxyApi(apiPath) {
    return proxyApiOrigin + syncApiPath + "/web-contents" + apiPath;
}

function getNewsApi() {
    return assemblyProxyApi("/news");
}

function getEffectsApi() {
    return assemblyProxyApi("/effect");
}

function getBannerApi() {
    return assemblyProxyApi("/banner");
}

function initProxyApi(origin) {
    if (origin) {
        proxyApiOrigin = origin;
    }
    newsApiUrl = getNewsApi();
    effectsApiUlr = getEffectsApi();
    bannerApiUrl = getBannerApi();
}

initProxyApi(window.location.origin);

/**
 * dynamic update_list start
 */
let getNewsTimes = 0;

var MORE_BTN_LABEL = {
    en: "Learn more",
    ko: "자세히 보기",
};

function genDynamicApiMethod(url, successCb) {
    let sendTimes = 0;
    let apiFun = function (clientType, lang) {
        sendTimes++;
        const isPC = clientType === "PC";
        $.ajax({
            url: url + "?clientType=" + clientType + "&lang=" + lang,
            type: "GET",
            contentType: "application/json",
            dataType: "json",
            success: function (res) {
                successCb(res.data || [], lang, isPC);
            },
            error: function (response, status) {
                console.log("get news response", response);
                console.log("get news status", status);
                if (sendTimes > maxSendTimes) {
                    return;
                }
                setTimeout(function () {
                    apiFun(clientType, lang);
                }, 3000);
            },
            timeout: 10000,
        });
    };

    return apiFun;
}

let getNews = genDynamicApiMethod(newsApiUrl, createNews);

function createNews(newList, lang, isPC) {
    var fragment = document.createDocumentFragment();
    for (let i = 0; i < newList.length; i++) {
        fragment.appendChild(createNew(newList[i], "news" + (i + 1), MORE_BTN_LABEL[lang] || MORE_BTN_LABEL.en, isPC));
    }

    const updateListEl = $(".update_list");
    if (updateListEl) {
        updateListEl.children().remove();
        updateListEl.append(fragment);
    }
}

function createNew(data, id, moreBtnLabel, isPC = true) {
    var rootEl = document.createElement("li");
    rootEl.id = id;
    var linkEl = document.createElement("a");
    linkEl.href = data.link;
    linkEl.target = "_blank";
    rootEl.appendChild(linkEl);

    var imgAreaEl = document.createElement("div");
    imgAreaEl.className = "img_area";
    imgAreaEl.style.backgroundImage = "url(" + data.bgLink + ")";
    imgAreaEl.style.backgroundSize = "contain";
    linkEl.appendChild(imgAreaEl);

    var iconEl = document.createElement("img");
    iconEl.className = "ico";
    iconEl.src = data.icon;
    iconEl.alt = "";
    imgAreaEl.appendChild(iconEl);
    // create info_area
    var infoAreaEl = document.createElement("div");
    infoAreaEl.className = "info_area";
    linkEl.appendChild(infoAreaEl);
    // create title
    var titleEl = document.createElement("strong");
    titleEl.className = "title";
    titleEl.innerText = data.title;
    infoAreaEl.appendChild(titleEl);
    // crate more_btn
    var moreBtnEl = document.createElement("span");
    moreBtnEl.className = "more_btn";
    moreBtnEl.innerText = moreBtnLabel;
    infoAreaEl.appendChild(moreBtnEl);
    if (isPC) {
        // crate go_arr
        var goArrEl = document.createElement("span");
        goArrEl.className = "go_arr";
        var blackArrEl = document.createElement("img");
        blackArrEl.src = "/img/more_btn_arr_black.png";
        blackArrEl.className = "black_arr";
        var blueArrEl = document.createElement("img");
        blueArrEl.src = "/img/more_btn_arr_blue.png";
        blueArrEl.className = "blue_arr";
        goArrEl.append(blackArrEl, blueArrEl);
        moreBtnEl.appendChild(goArrEl);
    }

    return rootEl;
}

function getPCNews(lang) {
    getNews("PC", lang);
}

function getMobileNews(lang) {
    getNews("Mobile", lang);
}

/**
 * dynamic update_list end
 */

/**
 * dynamic effect start
 */

let getEffects = genDynamicApiMethod(effectsApiUlr, createEffects)

function createEffects(effectList) {
    if (!effectList.length) {
        return;
    }

    var fragment = document.createDocumentFragment();
    for (let i = 0; i < effectList.length; i++) {
        var item = effectList[i];
        var el = document.createElement("li");
        el.style.background = "url(" + item.image + ") 0 0 / contain no-repeat";
        fragment.appendChild(el);
    }

    const newEffectWapper = document.querySelector(".new_effect_wrap");
    const updateListEl = $(".new_effect_wrap .effect_list");
    if (updateListEl) {
        updateListEl.children().remove();
        updateListEl.append(fragment);
        newEffectWapper.style.display = "block";
    }
}

function getPCEffects(lang) {
    getEffects("PC", lang);
}

function getMobileEffects(lang) {
    getEffects("Mobile", lang);
}

/**
 * dynamic effect end
 */

/**
 * dynamic banner start
 */

let getBanner = genDynamicApiMethod(bannerApiUrl, initBanner);

function initBanner(bannerInfoList, clientType, lang) {
    var banner = null;
    if (bannerInfoList && bannerInfoList.length) {
        banner = bannerInfoList[0];
    }

    if (!banner) {
        getBanner(clientType, lang);
        return;
    }

    const bannerLinkEl = document.querySelector(".wrap a.banner_area");
    const bannerContainer = bannerLinkEl && bannerLinkEl.querySelector(".inner");

    if (!bannerContainer) {
        return;
    }

    // bind banner link
    bannerLinkEl.href = banner.link;
    bannerLinkEl.style.overflow = "hidden";
    bannerLinkEl.style.display = "block";
    bannerLinkEl.style.backgroundColor = banner.colorCode;
    bannerContainer.style.boxShadow = "0 -5000px 0 5000px " + banner.colorCode;
    bannerContainer.style.background = "transparent";

    // update banner image.
    var bannerImgEl = bannerContainer.querySelector("img");
    bannerImgEl.src = banner.image;
    bannerImgEl.style.visibility = true;
}

function getPCBanner(lang) {
    getBanner("PC", lang);
}

function getMobileBanner(lang) {
    getBanner("Mobile", lang);
}

/**
 * dynamic banner end
 */
