$("#username").blur(function(){
    checkInput("#username",(!$(this).val() || !$(this).val().match(/.{1,30}$/)));
});
$("#email").blur(function(){
    checkInput("#email",(!$(this).val() || !$(this).val().match(/^(\w)+(\.\w+)*@(\w)+((\.\w+)+)$/)));
});
$("#password").blur(function(){
    checkInput("#password",(!$(this).val() || !$(this).val().match(/.{6,}$/)));
});
$("#password-ag").blur(function(){
    checkInput("#password-ag",($(this).val()!=$("#password").val()));
});
$("#username-t").hide();
$("#email-t").hide();
$("#password-t").hide();
$("#password-ag-t").hide();
$("#submit").click(function(){
    readySubmit=true;
    $("#username").blur();
    $("#email").blur();
    $("#password").blur();
    $("#password-ag").blur();
    if(!readySubmit)
        return false;
    $.post("/signup",{_xsrf:$("input[name='_xsrf']").val(),
            username:$("#username").val(),
            email:$("#email").val(),
            password:$("#password").val()},
        function(data){
            alert(data.message);
            if(data.status=="success"){
                if(args.next)
                    location.href=args.next;
                else
                    location.href="/";
            }
        },"json");
    return false;
});