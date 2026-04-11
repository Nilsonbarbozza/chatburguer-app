/* ── Bloco inline #9 (type=text/javascript) ── */
;(function() {
$(window).scroll(function() {
			if ($(this).scrollTop() > 0 ) {
				$('.header').addClass('scroll');
				$('.header').css('top' , '0');
				$('.top_btn').css('display' , 'block');
				$('.banner_area').css('display' , 'none');
				
			} else {
				$('.header').removeClass('scroll');
				$('.top_btn').css('display' , 'none');
				$('.banner_area').css('display' , 'block');
			}
		});  

		$('.question_area').click(function() {
				$(this).parent('li').toggleClass('open');
		});
})();

/* ── Bloco inline #10 (type=text/javascript) ── */
;(function() {
$(document).ready(function() {
			$('.function_list').slick({
             slidesToShow: 1,
             centerMode: true,
             focusOnSelect: true,
             arrows: true,
             dots: true,
             infinite: false,
             speed: 110,
			 fade: true,
             cssEase: 'linear'
			});
		
        const section = window.location.href.split('#')[1];
        let slide = 0;
        if (section === 'multistream') {
            slide = 0;
        } else if (section === 'screencast') {
            slide = 1;
        } else if (section === 'vtuber') {
            slide = 2;
        }
        if (section) {
            $('html, body').animate({
                scrollTop: $('#function').offset().top
            }, 0);
            $('.function_list').slick('slickGoTo', slide);
        }

        $(window).scroll(function(){
            var sectionTop = $(this).scrollTop();//window scroll값 변수로 지정
            $('.section').each(function(){
                var sctionOST = $(this).offset().top -500 ;//section top값 가져오기
                // var footer = $('.footer').offset().top -1000; // footer만 분기 
                    var sctionEffect = $(this).attr('data-effect');
                if(sectionTop >= sctionOST){
                    $(this).addClass(sctionEffect);
                }
            })
        })

        $('.slick-prev').click(function () {
            sendEventLog('slot1.prev');
        });
        $('.slick-next').click(function () {
            sendEventLog('slot1.next');
        });
    });
})();
