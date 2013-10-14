search = ->
  txt = $('.search-query').val()
  if not txt
    return false
  window.open "https://www.google.com/search?q=site:#{domain} #{txt}"
  $('.search-query').val('')
  return false

_ = (msg) ->
  return i18n[msg] if i18n?[msg]?
  return msg

window.notify = () ->
  setTimeout(window.notify, 30000)
  $.ajax
    url: "/api/notifications/new"
    success: (data) ->
      if not data.id?
        return
      last_id = window.localStorage.getItem('last_notify')
      window.localStorage.setItem('last_notify', data.id)
      for notification in data.notifications
        if notification.id == last_id
          return
        $.notifier.notify(notification.avatar, notification.title,
        notification.content, notification.url)
      return

floor_link_page = ->
  floor_link = $(".mention.mention_floor")
  for i in floor_link
    floor_num = new Number(i.href.match(/#reply(\d+)/)[1])
    floor_page = new Number(
      (floor_num + @replies_per_page - 1) / @replies_per_page)
    floor_page = parseInt(floor_page)
    i.href = "?p=#{floor_page}#reply#{floor_num}"
  return

topic_link = ->
  element = $(".mention.mention_topic")
  elements = {}
  for i in element
    _id = $(i).attr("_id")
    if not elements[_id]
      elements[_id] = []
    elements[_id].push({"_id": _id, "object": i})
    $.ajax({
      url: "/api/topic/#{_id}",
      cache: false,
      success: (data) ->
        object = elements[data._id][0].object
        object.innerHTML = data.title
        object.title = data.content.slice(0, 30)
        if data.content.length > 30
          object.title += "..."
        elements[data._id] = elements[data._id].slice(1)
        return
    })
  return

$ ->
  notify()
  $('time').timeago()
  $('.dangerous').click ->
    if window.confirm(_('Are you sure?'))
      window.location = $(this).data('href')
    return false
  $('.remove').click ->
    $this = $(this)
    url = $this.data('href')
    if window.confirm(_('Are you sure?'))
      type = $this.data('type')
      $.post url, ->
        if type == "topic"
          window.location.href = "/"
        else
          $this.parents(".list").remove()
    return false
  floor_link_page()
  topic_link()
  return
