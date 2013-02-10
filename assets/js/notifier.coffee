class Notifier
    constructor: ->
        @enableNotification = false
        @checkOrRequirePermission()

    hasSupport: ->
        window.webkitNotifications?

    requestPermission: (cb) ->
        window.webkitNotifications.requestPermission (cb)

    setPermission: =>
        if @hasPermission()
            $('#notification-alert a.close').click()
            @enableNotification = true
        else if window.webkitNotifications.checkPermission() is 2
            $('#notification-alert a.close').click()

    hasPermission: ->
        if window.webkitNotifications.checkPermission() is 0
            return true
        else
            return false

    checkOrRequirePermission: =>
        if @hasSupport()
            if @hasPermission()
                @enableNotification = true
            else
                if window.webkitNotifications.checkPermission() isnt 2
                    @showTooltip()
        else
            console.log("Desktop notifications are not supported for this Browser/OS version yet.")

    showTooltip: ->
        $('#messages').append("<div class='alert alert-info' id='notification-alert'><a href='#' id='link_enable_notifications' style='color:green'>Click here</a> to enable Desktop Notification。 <a class='close' data-dismiss='alert' href='#'>×</a></div>")
        $("#notification-alert").alert()
        $('#notification-alert').on 'click', 'a#link_enable_notifications', (e) =>
            e.preventDefault()
            @requestPermission(@setPermission)

    visitUrl: (url) ->
        window.location.href = url

    notify: (avatar, title, content, url = null) ->
        if @enableNotification
            popup = window.webkitNotifications.createNotification(avatar, title, content)  #TODO:there is a lot of bugs
            if url
                popup.onclick = ->
                    window.focus()
                    $.notifier.visitUrl(url)
                    popup.close()
            popup.show()

jQuery.notifier = new Notifier