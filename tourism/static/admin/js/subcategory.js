window.addEventListener("load", function() {
    (function($) {
        function getSubCategories(id, selected) {
            $.ajax({
                type: 'GET',
                url: "/get/admin/subcategory",
                data: {"id": id},
                success: function (response) {
                    var options = '<option value=""'
                    options += (selected == 0) ? ' selected=""' : ''
                    options += '>---------</option>'
                    for (const subcategory of Object.values(response["subcategories"])){
                        console.log(selected, subcategory.id, selected == subcategory.id)
                        options += '<option value="' + subcategory.id + '"'
                        options += (selected == subcategory.id) ? ' selected=""' : ''
                        options += '>' + subcategory.name + "</option>";
                    }
                    $("select#id_subcategory").html(options);
                },
                error: function(response) {
                    console.log("Échec de la requête AJAX (loadSubCat)");
                    // console.log(response);
                }
            })
        }

        $(document).ready(function(){
            getSubCategories($("select#id_category").val(), $("select#id_subcategory").val());
        });
    
        $("select#id_category").change(function(){
            getSubCategories($(this).val(), 0);
        });
        // });
    })(django.jQuery);
});