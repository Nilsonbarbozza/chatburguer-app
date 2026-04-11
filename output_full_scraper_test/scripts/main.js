/* ── Bloco inline #13 (type=text/javascript) ── */
;(function() {
var swiper = new Swiper(".filter_area", {
            autoplay: {
                delay: 0,
                stopOnLastSlide: false,
                disableOnInteraction: false,
            },
            speed: 5000,
            loop: true,
            slidesPerView: "auto",
            loopedSlides: 8, //noSwiping : true,
            observer: true, observeParents: true,
        });

    $(window).scroll(function () {
        if ($(this).scrollTop() > 0) {
            $('.header').addClass('scroll');
            $('.header').css('top', '0');
            $('.top_btn').css('display', 'block');
            $('.banner_area').css('display', 'none');
            
        } else {
            $('.header').removeClass('scroll');
            $('.top_btn').css('display', 'none');
            $('.banner_area').css('display', 'block');
            // $('.header').css('top' , '68px');
        }
    });    

    getPCEffects('en');
})();
