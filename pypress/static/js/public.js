var ajax_post = function(url, params, on_success){
	var _callback = function(response){
		if (response.success) {
			if (response.redirect_url){
				window.location.href = response.redirect_url;
			} else if (response.reload){
				window.location.reload(); 
			} else if (on_success) {
				return on_success(response);
			}
		} else  {
			return message(response.error, "error");
		}
	}

	$.post(url, params, _callback, "json");

}

var message = function(message, category){
	$('ul#messages').html('<li class="' + category + '">' + message + '</li>').fadeOut();
}

var delete_comment = function(url) {
	var callback = function(response){
		$('#comment-' + response.comment_id).fadeOut();
	}   
	ajax_post(url, null, callback);
}

var delete_link = function(url) {
	var callback = function(response){
		$('#link-' + response.link_id).fadeOut();
	}   
	ajax_post(url, null, callback);
}

var pass_link = function(url) {
	var callback = function(response){
		$('#link-' + response.link_id).find('.link-edit').remove();
	}
	ajax_post(url, null, callback);
}

var hide_flash = function(){
    $("#flashed").fadeOut();
}

$(function(){
    setTimeout(hide_flash, 3000);
})
