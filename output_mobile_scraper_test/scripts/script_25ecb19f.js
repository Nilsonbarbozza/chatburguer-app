const header = {
    en:`<div class="header_inner">
    <div class="content_left">
        <h1 class="logo">
            <a href="#">PRISM Live Studio</a>
        </h1>
        <div class="menu">
            <ul class="menu_list">
                <!-- li 선택시 li 에 on 클래스 추가 -->
                <li class="gnb">
                    <a href="#">
                        <span class="title1">Product</span>
                    </a>
                    <div class="box">
                        <div class="submenu_box type_app">
                            <div class="submenu_content">
                                <ul class="submenu_list">
                                    <li class="mobileP">
                                        <a href="#" class="app_name">
                                            <div class="img_area">
                                                <img src="/img/header_icon_01.png" alt="">
                                            </div>
                                            <div class="text_area">
                                                <span>PRISM Live Studio</span>
                                                <span>Mobile app</span>
                                            </div>
                                        </a>
                                    </li>
                                    <li class="desktopP">
                                        <a href="#" class="app_name">
                                            <div class="img_area">
                                                <img src="/img/header_icon_01.png" alt="">
                                            </div>
                                            <div class="text_area">
                                                <span>PRISM Live Studio</span>
                                                <span>Desktop app</span>
                                            </div>
                                        </a>
                                    </li>
                                    <li class="lensP">
                                        <a href="#" class="app_name">
                                            <div class="img_area">
                                                <img src="/img/header_icon_02.png" alt="">
                                            </div>
                                            <div class="text_area">
                                                <span>PRISM Lens</span>
                                                <span>Desktop app</span>
                                            </div>
                                        </a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </li>
                <li class="effectP">
                    <a href="#">
                        <span class="title2">Effects</span>
                    </a>
                </li>
                <li class="gnb"> 
                    <a href="#">
                        <span class="title3">Community</span>
                    </a>
                    <div class="box">
                        <div class="submenu_box">
                            <div class="submenu_content">
                                <ul class="submenu_list">
                                    <li class="type_arr user-guide"><a href="#">User Guide</a></li>
                                    <li class="type_arr discord"><a href="#">Discord</a></li>
                                    <li class="type_arr youtube"><a href="#">Youtube</a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </li>
                <li class="header-plus">
                    <a href="#">
                        <span class="title4">PRISM Plus</span>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    <div class="content_right">
        <button type="button" class="download_btn">
            Download
        </button>
        <div class="box">
            <div class="download_box">
                <div class="live_studio_area">
                    <strong class="title"><span class="blind">PRISM Live Studio</span></strong>
                    <ul>
                        <li class="windows win64_studio">
                            <a href="#">
                                <span class="blind">Download for Windows</span>
                            </a>
                        </li>
                        <li class="mac mac_studio">
                            <a href="#">
                                <span class="blind">Download for macOS</span>
                            </a>
                        </li>
                    </ul>
                    <ul class="qr_area">
                        <li class="android">
                            <img src="../img/qr_android_v2.png" alt="Android QR">
                        </li>
                        <li class="ios">
                            <img src="../img/qr_ios_v2.png" alt="iOS QR">
                        </li>
                    </ul>
                    <p class="text">
                        Scan the QR code <br>
                        to download the mobile app.
                    </p>
                </div>
                <div class="lens_area">
                    <strong class="title"><span class="blind">PRISM Lens</span></strong>
                    <ul>
                        <li class="windows win64_lens">
                            <a href="#">
                                <span class="blind">Download for Windows</span>
                            </a>
                        </li>
                        <li class="mac mac_lens">
                            <a href="#">
                                <span class="blind">Download for macOS</span>
                            </a>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>
            `,
    ko:`
<div class="header_inner">
    <div class="content_left">
        <h1 class="logo">
            <a href="#">PRISM Live Studio</a>
        </h1>
        <div class="menu">
            <ul class="menu_list">
                <!-- li 선택시 li 에 on 클래스 추가 -->
                <li class="gnb">
                    <a href="#">
                        <span class="title1">제품</span>
                    </a>
                    <div class="box">
                        <div class="submenu_box type_app">
                            <div class="submenu_content">
                                <ul class="submenu_list">
                                    <li class="mobileP">
                                        <a href="#" class="app_name">
                                            <div class="img_area">
                                                <img src="/img/header_icon_01.png" alt="">
                                            </div>
                                            <div class="text_area">
                                                <span>PRISM Live Studio</span>
                                                <span>모바일 앱</span>
                                            </div>
                                        </a>
                                    </li>
                                    <li class="desktopP">
                                        <a href="#" class="app_name">
                                            <div class="img_area">
                                                <img src="/img/header_icon_01.png" alt="">
                                            </div>
                                            <div class="text_area">
                                                <span>PRISM Live Studio</span>
                                                <span>데스크톱 앱</span>
                                            </div>
                                        </a>
                                    </li>
                                    <li class="lensP">
                                        <a href="#" class="app_name">
                                            <div class="img_area">
                                                <img src="/img/header_icon_02.png" alt="">
                                            </div>
                                            <div class="text_area">
                                                <span>PRISM Lens</span>
                                                <span>데스크톱 앱</span>
                                            </div>
                                        </a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </li>
                <li class="effectP">
                    <a href="#">
                        <span class="title2">이펙트</span>
                    </a>
                </li>
                <li class="gnb">
                    <a href="#">
                        <span class="title3">커뮤니티</span>
                    </a>
                    <div class="box">
                        <div class="submenu_box">
                            <div class="submenu_content">
                                <ul class="submenu_list">
                                    <li class="type_arr user-guide"><a href="#">사용자 가이드</a></li>
                                    <li class="type_arr discord"><a href="#">디스코드</a></li>
                                    <li class="type_arr youtube"><a href="#">유튜브</a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </li>
                <li class="header-plus">
                    <a href="#">
                        <span class="title4">PRISM Plus</span>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    <div class="content_right">
        <button type="button" class="download_btn">
            다운로드
        </button>
        <div class="box">
            <div class="download_box">
                <div class="live_studio_area">
                    <strong class="title"><span class="blind">PRISM Live Studio</span></strong>
                    <ul>
                        <li class="windows win64_studio">
                            <a href="#">
                                <span class="blind">Download for Windows</span>
                            </a>
                        </li>
                        <li class="mac mac_studio">
                            <a href="#">
                                <span class="blind">Download for macOS</span>
                            </a>
                        </li>
                    </ul>
                    <ul class="qr_area">
                        <li class="android">
                            <img src="/img/qr_android_v2.png" alt="Android QR">
                        </li>
                        <li class="ios">
                            <img src="/img/qr_ios_v2.png" alt="iOS QR">
                        </li>
                    </ul>
                    <p class="text">
                        QR코드를 스캔하면 <br>
                        모바일앱을 다운받으실 수 있습니다.
                    </p>
                </div>
                <div class="lens_area">
                    <strong class="title"><span class="blind">PRISM Lens</span></strong>
                    <ul>
                        <li class="windows win64_lens">
                            <a href="#">
                                <span class="blind">Download for Windows</span>
                            </a>
                        </li>
                        <li class="mac mac_lens">
                            <a href="#">
                                <span class="blind">Download for macOS</span>
                            </a>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>`
}
const footer = {
    en:`<div class="inner">
    <div class="contents">
        <div class="contents_wrap">
            <ul class="footer_menu">
                <li>
                    <dl>
                        <dt>Product</dt>
                        <dd class="mobileP"><a href="#">PRISM Live mobile app</a></dd>
                        <dd class="desktopP"><a href="#">PRISM Live desktop app</a></dd>
                        <dd class="lensP"><a href="#">PRISM Lens desktop app</a></dd>
                    </dl>
                </li>
                <li>
                    <dl>
                        <dt>About Effects</dt>
                        <dd class="effectP"><a href="#">Effects</a></dd>
                        <dd class="giphy"><a href="#">GIPHY</a></dd>
                    </dl>
                </li>
                <li>
                    <dl>
                        <dt>Community</dt>
                        <dd class="user-guide"><a href="https://guide.prismlive.com">User guide</a></dd>
                        <dd class="discord"><a href="#">Discord</a></dd>
                        <dd class="youtube"><a href="#">Youtube</a></dd>
                    </dl>
                </li>
                <li>
                    <dl>
                        <dt>PRISM Plus</dt>
                        <dd class="footer-plus"><a href="#">About PRISM Plus</a></dd>
                    </dl>
                </li>
                <li>
                    <dl>
                        <dt>Help</dt>
                        <dd class="faq-mapp"><a href="#">PRISM Live mobile app</a></dd>
                        <dd class="faq-pcapp"><a href="#">PRISM Live desktop app</a></dd>
                        <dd class="faq-lens"><a href="#">PRISM Lens desktop app</a></dd>
                    </dl>
                </li>
            </ul>
            <div class="lang_select"> 
                <div class="selected_btn">
                    <button type="button">
                        English
                    </button>
                </div>
                <ul class="lang_list">
                    <li class="ko_kr"><a href="#">한국어</a></li>
                    <li class="en_us"><a href="#">English</a></li>
                </ul>
            </div>
        </div>
    </div>
    <div class="contents">
        <div class="business_info">
            <div>
                <dl class="info_group">
                    <dt>CEO of NAVER Corp. :</dt>
                    <dd>Choi Soo Yeon</dd>
                    <dt>Business Registration Number :</dt>
                    <dd>220-81-62517</dd>
                    <dt>E-commerce Registration Number :</dt>
                    <dd>No. 2009-GyeonggiSeongnam-0692</dd>
                </dl>
                <dl class="info_group">
                    <dt>Address :</dt>
                    <dd>NAVER 1784, 95, Jeongjail-ro, Bundang-gu, Seongnam-si, Gyeonggi-do, Republic of Korea</dd>
                    <dt>Main Contact :</dt>
                    <dd>1588-3820</dd>
                    <dt>Email :</dt>
                    <dd>prismlive@navercorp.com</dd>
                </dl>
            </div>
            <div class="sns">
                <span class="youtube"><a href="#">youtube</a></span>
                <span class="discord"><a href="#">discord</a></span>
            </div>
        </div>
        <div class="contents_wrap">
            <a href="#" class="logo">
                <span class="blind">PRISM Live Studio</span>
            </a>
            <a href="#" class="copyright" target="_blank">
                <span>NAVER Corp. All rights reserved.</span>
            </a>
            <div class="notice">
                <span class="terms"><a href="#">Terms of Use</a></span>
                <span class="bold privacy"><a href="#">Privacy Policy</a></span>
                <span class="signout"><a href="#">Delete your account</a></span>
            </div>
        </div>
    </div>
</div>`,
    ko:`
<div class="inner">
    <div class="contents">
        <div class="contents_wrap">
            <ul class="footer_menu">
                <li>
                    <dl>
                        <dt>제품</dt>
                        <dd class="mobileP"><a href="#">PRISM Live 모바일 앱</a></dd>
                        <dd class="desktopP"><a href="#">PRISM Live 데스크톱 앱</a></dd>
                        <dd class="lensP"><a href="#">PRISM Lens 데스크톱 앱</a></dd>
                    </dl>
                </li>
                <li>
                    <dl>
                        <dt>이펙트에 대해</dt>
                        <dd class="effectP"><a href="#">이펙트</a></dd>
                        <dd class="giphy"><a href="#">GIPHY</a></dd>
                    </dl>
                </li>
                <li>
                    <dl>
                        <dt>커뮤니티</dt>
                        <dd class="user-guide"><a href="https://guide.prismlive.com">사용자 가이드</a></dd>
                        <dd class="discord"><a href="#">디스코드</a></dd>
                        <dd class="youtube"><a href="#">유튜브</a></dd>
                    </dl>
                </li>
                <li>
                    <dl>
                        <dt>PRISM Plus</dt>
                        <dd class="footer-plus"><a href="#">PRISM Plus 소개</a></dd>
                    </dl>
                </li>
                <li>
                    <dl>
                        <dt>도움말</dt>
                        <dd class="faq-mapp"><a href="#">PRISM Live 모바일 앱</a></dd>
                        <dd class="faq-pcapp"><a href="#">PRISM Live 데스크톱 앱</a></dd>
                        <dd class="faq-lens"><a href="#">PRISM Lens 데스크톱 앱</a></dd>
                    </dl>
                </li>
            </ul>
            <div class="lang_select">
                <div class="selected_btn">
                    <button type="button">
                        한국어
                    </button>
                </div>
                <ul class="lang_list">
                    <li class="ko_kr"><a href="#">한국어</a></li>
                    <li class="en_us"><a href="#">English</a></li>
                </ul>
            </div>
        </div>
    </div>
    <div class="contents">
        <div class="business_info">
            <div>
                <dl class="info_group">
                    <dt>네이버(주) 대표이사 :</dt>
                    <dd>최수연</dd>
                    <dt>사업자 등록번호 :</dt>
                    <dd>220-81-62517</dd>
                    <dt>통신판매업 신고번호 :</dt>
                    <dd>제2006-경기성남-0692호</dd>
                </dl>
                <dl class="info_group">
                    <dt>주소 :</dt>
                    <dd>경기도 성남시 분당구 정자일로 95, NAVER 1784, 13561</dd>
                    <dt>대표전화 :</dt>
                    <dd>1588-3820</dd>
                    <dt>이메일 :</dt>
                    <dd>prismlive@navercorp.com</dd>
                </dl>
            </div>
            <div class="sns">
                <span class="youtube"><a href="#">youtube</a></span>
                <span class="discord"><a href="#">discord</a></span>
            </div>
        </div>
        <div class="contents_wrap">
            <a href="#" class="logo">
                <span class="blind">PRISM Live Studio</span>
            </a>
            <a href="#" class="copyright" target="_blank">
                <span>NAVER Corp. All rights reserved.</span>
            </a>
            <div class="notice">
                <span class="terms"><a href="#">이용약관</a></span>
                <span class="bold privacy"><a href="#">개인정보처리방침</a></span>
                <span class="signout"><a href="#">회원 탈퇴</a></span>
            </div>
        </div>
    </div>
</div>`
}

$(document).ready(function () {
    var lang = $('html').attr('lang');
    window.__IS_PC_PAGE__ = true; // PC 페이지: promotion_code 등 전달용
    // 인클루드 적용
    $('.insert-header').html(header[lang === 'ko' ? 'ko' : 'en']);
    $('.insert-footer').html(footer[lang === 'ko' ? 'ko' : 'en']);
});