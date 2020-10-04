window.addEventListener("load", function() {
    hide_page=false;
    django.jQuery(document).ready(function(){
        if (django.jQuery('#id_is_always_open').is(':checked')) {
            django.jQuery("#openingperiod_set-group").hide(500);
            hide_page=true;
        } else {
            django.jQuery("#openingperiod_set-group").show(500);
            hide_page=false;
        }
        django.jQuery("#id_is_always_open").click(function(){
            hide_page=!hide_page;
            if (hide_page) {
                django.jQuery("#openingperiod_set-group").hide(500);
            } else {
                django.jQuery("#openingperiod_set-group").show(500);
            }
        })
    })
});