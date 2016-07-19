import io
import json
import time
import asyncio
import traceback
import collections
from concurrent.futures._base import CancelledError
from . import helper, api
from .. import _BotBase, flavor, _find_first_key, _isstring, _dismantle_message_identifier, _strip, _rectify

# Patch aiohttp for sending unicode filename
from . import hack


def flavor_router(routing_table):
    router = helper.Router(flavor, routing_table)
    return router.route


class Bot(_BotBase):
    def __init__(self, token, loop=None):
        super(Bot, self).__init__(token)
        self._loop = loop if loop is not None else asyncio.get_event_loop()

        self._router = helper.Router(flavor, {'chat': helper._delay_yell(self, 'on_chat_message'),
                                              'edited_chat': helper._delay_yell(self, 'on_edited_chat_message'),
                                              'callback_query': helper._delay_yell(self, 'on_callback_query'),
                                              'inline_query': helper._delay_yell(self, 'on_inline_query'),
                                              'chosen_inline_result': helper._delay_yell(self, 'on_chosen_inline_result')})

    @property
    def loop(self):
        return self._loop

    async def handle(self, msg):
        await self._router.route(msg)

    async def _api_request(self, method, params=None, files=None, **kwargs):
        return await api.request((self._token, method, params, files), **kwargs)

    async def getMe(self):
        """ See: https://core.telegram.org/bots/api#getme """
        return await self._api_request('getMe')

    async def sendMessage(self, chat_id, text,
                          parse_mode=None, disable_web_page_preview=None,
                          disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendmessage """
        p = _strip(locals())
        return await self._api_request('sendMessage', _rectify(p))

    async def forwardMessage(self, chat_id, from_chat_id, message_id, disable_notification=None):
        """ See: https://core.telegram.org/bots/api#forwardmessage """
        p = _strip(locals())
        return await self._api_request('forwardMessage', _rectify(p))

    async def _sendfile(self, inputfile, filetype, params):
        method = {'photo':    'sendPhoto',
                  'audio':    'sendAudio',
                  'document': 'sendDocument',
                  'sticker':  'sendSticker',
                  'video':    'sendVideo',
                  'voice':    'sendVoice',}[filetype]

        if _isstring(inputfile):
            params[filetype] = inputfile
            return await self._api_request(method, _rectify(params))
        else:
            files = {filetype: inputfile}
            return await self._api_request(method, _rectify(params), files)

    async def sendPhoto(self, chat_id, photo,
                        caption=None,
                        disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendphoto

        :param photo:
            a string indicating a ``file_id`` on server,
            a file-like object as obtained by ``open()`` or ``urlopen()``,
            or a (filename, file-like object) tuple.
            If the file-like object is obtained by ``urlopen()``, you most likely
            have to supply a filename because Telegram servers require to know
            the file extension.
            If the filename contains non-ASCII characters and you are using Python 2.7,
            make sure the filename is a unicode string.
        """
        p = _strip(locals(), more=['photo'])
        return await self._sendfile(photo, 'photo', p)

    async def sendAudio(self, chat_id, audio,
                        duration=None, performer=None, title=None,
                        disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendaudio

        :param audio: Same as ``photo`` in :meth:`telepot.aio.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['audio'])
        return await self._sendfile(audio, 'audio', p)

    async def sendDocument(self, chat_id, document,
                           caption=None,
                           disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#senddocument

        :param document: Same as ``photo`` in :meth:`telepot.aio.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['document'])
        return await self._sendfile(document, 'document', p)

    async def sendSticker(self, chat_id, sticker,
                          disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendsticker

        :param sticker: Same as ``photo`` in :meth:`telepot.aio.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['sticker'])
        return await self._sendfile(sticker, 'sticker', p)

    async def sendVideo(self, chat_id, video,
                        duration=None, width=None, height=None, caption=None,
                        disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendvideo

        :param video: Same as ``photo`` in :meth:`telepot.aio.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['video'])
        return await self._sendfile(video, 'video', p)

    async def sendVoice(self, chat_id, voice,
                        duration=None,
                        disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#sendvoice

        :param voice: Same as ``photo`` in :meth:`telepot.aio.Bot.sendPhoto`
        """
        p = _strip(locals(), more=['voice'])
        return await self._sendfile(voice, 'voice', p)

    async def sendLocation(self, chat_id, latitude, longitude,
                           disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendlocation """
        p = _strip(locals())
        return await self._api_request('sendLocation', _rectify(p))

    async def sendVenue(self, chat_id, latitude, longitude, title, address,
                        foursquare_id=None,
                        disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendvenue """
        p = _strip(locals())
        return await self._api_request('sendVenue', _rectify(p))

    async def sendContact(self, chat_id, phone_number, first_name,
                          last_name=None,
                          disable_notification=None, reply_to_message_id=None, reply_markup=None):
        """ See: https://core.telegram.org/bots/api#sendcontact """
        p = _strip(locals())
        return await self._api_request('sendContact', _rectify(p))

    async def sendChatAction(self, chat_id, action):
        """ See: https://core.telegram.org/bots/api#sendchataction """
        p = _strip(locals())
        return await self._api_request('sendChatAction', _rectify(p))

    async def getUserProfilePhotos(self, user_id, offset=None, limit=None):
        """ See: https://core.telegram.org/bots/api#getuserprofilephotos """
        p = _strip(locals())
        return await self._api_request('getUserProfilePhotos', _rectify(p))

    async def getFile(self, file_id):
        """ See: https://core.telegram.org/bots/api#getfile """
        p = _strip(locals())
        return await self._api_request('getFile', _rectify(p))

    async def kickChatMember(self, chat_id, user_id):
        """ See: https://core.telegram.org/bots/api#kickchatmember """
        p = _strip(locals())
        return await self._api_request('kickChatMember', _rectify(p))

    async def leaveChat(self, chat_id):
        """ See: https://core.telegram.org/bots/api#leavechat """
        p = _strip(locals())
        return await self._api_request('leaveChat', _rectify(p))

    async def unbanChatMember(self, chat_id, user_id):
        """ See: https://core.telegram.org/bots/api#unbanchatmember """
        p = _strip(locals())
        return await self._api_request('unbanChatMember', _rectify(p))

    async def getChat(self, chat_id):
        """ See: https://core.telegram.org/bots/api#getchat """
        p = _strip(locals())
        return await self._api_request('getChat', _rectify(p))

    async def getChatAdministrators(self, chat_id):
        """ See: https://core.telegram.org/bots/api#getchatadministrators """
        p = _strip(locals())
        return await self._api_request('getChatAdministrators', _rectify(p))

    async def getChatMembersCount(self, chat_id):
        """ See: https://core.telegram.org/bots/api#getchatmemberscount """
        p = _strip(locals())
        return await self._api_request('getChatMembersCount', _rectify(p))

    async def getChatMember(self, chat_id, user_id):
        """ See: https://core.telegram.org/bots/api#getchatmember """
        p = _strip(locals())
        return await self._api_request('getChatMember', _rectify(p))

    async def answerCallbackQuery(self, callback_query_id, text=None, show_alert=None):
        """ See: https://core.telegram.org/bots/api#answercallbackquery """
        p = _strip(locals())
        return await self._api_request('answerCallbackQuery', _rectify(p))

    async def editMessageText(self, msg_identifier, text,
                              parse_mode=None, disable_web_page_preview=None, reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#editmessagetext

        :param msg_identifier:
            a 2-tuple (``chat_id``, ``message_id``),
            a 1-tuple (``inline_message_id``),
            or simply ``inline_message_id``.
            You may extract this value easily with :meth:`telepot.message_identifier`
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return await self._api_request('editMessageText', _rectify(p))

    async def editMessageCaption(self, msg_identifier, caption=None, reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#editmessagecaption

        :param msg_identifier: Same as ``msg_identifier`` in :meth:`telepot.aio.Bot.editMessageText`
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return await self._api_request('editMessageCaption', _rectify(p))

    async def editMessageReplyMarkup(self, msg_identifier, reply_markup=None):
        """
        See: https://core.telegram.org/bots/api#editmessagereplymarkup

        :param msg_identifier: Same as ``msg_identifier`` in :meth:`telepot.aio.Bot.editMessageText`
        """
        p = _strip(locals(), more=['msg_identifier'])
        p.update(_dismantle_message_identifier(msg_identifier))
        return await self._api_request('editMessageReplyMarkup', _rectify(p))

    async def answerInlineQuery(self, inline_query_id, results,
                                cache_time=None, is_personal=None, next_offset=None,
                                switch_pm_text=None, switch_pm_parameter=None):
        """ See: https://core.telegram.org/bots/api#answerinlinequery """
        p = _strip(locals())
        return await self._api_request('answerInlineQuery', _rectify(p))

    async def getUpdates(self, offset=None, limit=None, timeout=None):
        """ See: https://core.telegram.org/bots/api#getupdates """
        p = _strip(locals())
        return await self._api_request('getUpdates', _rectify(p))

    async def setWebhook(self, url=None, certificate=None):
        """ See: https://core.telegram.org/bots/api#setwebhook """
        p = _strip(locals(), more=['certificate'])

        if certificate:
            files = {'certificate': certificate}
            return await self._api_request('setWebhook', _rectify(p), files)
        else:
            return await self._api_request('setWebhook', _rectify(p))

    async def download_file(self, file_id, dest):
        """
        Download a file to local disk.

        :param dest: a path or a ``file`` object
        """
        f = await self.getFile(file_id)

        try:
            d = dest if isinstance(dest, io.IOBase) else open(dest, 'wb')

            async with api.download((self._token, f['file_path'])) as r:
                while 1:
                    chunk = await r.content.read(self._file_chunk_size)
                    if not chunk:
                        break
                    d.write(chunk)
                    d.flush()
        finally:
            if not isinstance(dest, io.IOBase) and 'd' in locals():
                d.close()

    async def message_loop(self, handler=None, source=None, ordered=True, maxhold=3, timeout=20):
        """
        Return a task to constantly ``getUpdates`` or pull updates from a queue.
        Apply ``handler`` to every message received.

        :param handler:
            a function that takes one argument (the message), or a routing table.
            If ``None``, the bot's ``handle`` method is used.

        A *routing table* is a dictionary of ``{flavor: function}``, mapping messages to appropriate
        handler functions according to their flavors. It allows you to define functions specifically
        to handle one flavor of messages. It usually looks like this: ``{'chat': fn1,
        'callback_query': fn2, 'inline_query': fn3, ...}``. Each handler function should take
        one argument (the message).

        :param source:
            Source of updates.
            If ``None``, ``getUpdates`` is used to obtain new messages from Telegram servers.
            If it is a ``asyncio.Queue``, new messages are pulled from the queue.
            A web application implementing a webhook can dump updates into the queue,
            while the bot pulls from it. This is how telepot can be integrated with webhooks.

        Acceptable contents in queue:

        - ``str`` or ``bytes`` (decoded using UTF-8)
          representing a JSON-serialized `Update <https://core.telegram.org/bots/api#update>`_ object.
        - a ``dict`` representing an Update object.

        When ``source`` is a queue, these parameters are meaningful:

        :type ordered: bool
        :param ordered:
            If ``True``, ensure in-order delivery of messages to ``handler``
            (i.e. updates with a smaller ``update_id`` always come before those with
            a larger ``update_id``).
            If ``False``, no re-ordering is done. ``handler`` is applied to messages
            as soon as they are pulled from queue.

        :type maxhold: float
        :param maxhold:
            Applied only when ``ordered`` is ``True``. The maximum number of seconds
            an update is held waiting for a not-yet-arrived smaller ``update_id``.
            When this number of seconds is up, the update is delivered to ``handler``
            even if some smaller ``update_id``\s have not yet arrived. If those smaller
            ``update_id``\s arrive at some later time, they are discarded.

        :type timeout: int
        :param timeout:
            ``timeout`` parameter supplied to :meth:`telepot.aio.Bot.getUpdates`,
            controlling how long to poll in seconds.
        """
        if handler is None:
            handler = self.handle
        elif isinstance(handler, dict):
            handler = flavor_router(handler)

        def create_task_for(msg):
            self.loop.create_task(handler(msg))

        if asyncio.iscoroutinefunction(handler):
            callback = create_task_for
        else:
            callback = handler

        def handle(update):
            try:
                key = _find_first_key(update, ['message',
                                               'edited_message',
                                               'callback_query',
                                               'inline_query',
                                               'chosen_inline_result'])

                callback(update[key])
            except:
                # Localize the error so message thread can keep going.
                traceback.print_exc()
            finally:
                return update['update_id']

        async def get_from_telegram_server():
            offset = None  # running offset
            while 1:
                try:
                    result = await self.getUpdates(offset=offset, timeout=timeout)

                    if len(result) > 0:
                        # No sort. Trust server to give messages in correct order.
                        # Update offset to max(update_id) + 1
                        offset = max([handle(update) for update in result]) + 1
                except CancelledError:
                    raise
                except:
                    traceback.print_exc()
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0.1)

        def dictify(data):
            if type(data) is bytes:
                return json.loads(data.decode('utf-8'))
            elif type(data) is str:
                return json.loads(data)
            elif type(data) is dict:
                return data
            else:
                raise ValueError()

        async def get_from_queue_unordered(qu):
            while 1:
                try:
                    data = await qu.get()
                    update = dictify(data)
                    handle(update)
                except:
                    traceback.print_exc()

        async def get_from_queue(qu):
            # Here is the re-ordering mechanism, ensuring in-order delivery of updates.
            max_id = None                 # max update_id passed to callback
            buffer = collections.deque()  # keep those updates which skip some update_id
            qwait = None                  # how long to wait for updates,
                                          # because buffer's content has to be returned in time.

            while 1:
                try:
                    data = await asyncio.wait_for(qu.get(), qwait)
                    update = dictify(data)

                    if max_id is None:
                        # First message received, handle regardless.
                        max_id = handle(update)

                    elif update['update_id'] == max_id + 1:
                        # No update_id skipped, handle naturally.
                        max_id = handle(update)

                        # clear contagious updates in buffer
                        if len(buffer) > 0:
                            buffer.popleft()  # first element belongs to update just received, useless now.
                            while 1:
                                try:
                                    if type(buffer[0]) is dict:
                                        max_id = handle(buffer.popleft())  # updates that arrived earlier, handle them.
                                    else:
                                        break  # gap, no more contagious updates
                                except IndexError:
                                    break  # buffer empty

                    elif update['update_id'] > max_id + 1:
                        # Update arrives pre-maturely, insert to buffer.
                        nbuf = len(buffer)
                        if update['update_id'] <= max_id + nbuf:
                            # buffer long enough, put update at position
                            buffer[update['update_id'] - max_id - 1] = update
                        else:
                            # buffer too short, lengthen it
                            expire = time.time() + maxhold
                            for a in range(nbuf, update['update_id']-max_id-1):
                                buffer.append(expire)  # put expiry time in gaps
                            buffer.append(update)

                    else:
                        pass  # discard

                except asyncio.TimeoutError:
                    # debug message
                    # print('Timeout')

                    # some buffer contents have to be handled
                    # flush buffer until a non-expired time is encountered
                    while 1:
                        try:
                            if type(buffer[0]) is dict:
                                max_id = handle(buffer.popleft())
                            else:
                                expire = buffer[0]
                                if expire <= time.time():
                                    max_id += 1
                                    buffer.popleft()
                                else:
                                    break  # non-expired
                        except IndexError:
                            break  # buffer empty
                except:
                    traceback.print_exc()
                finally:
                    try:
                        # don't wait longer than next expiry time
                        qwait = buffer[0] - time.time()
                        if qwait < 0:
                            qwait = 0
                    except IndexError:
                        # buffer empty, can wait forever
                        qwait = None

                    # debug message
                    # print ('Buffer:', str(buffer), ', To Wait:', qwait, ', Max ID:', max_id)

        if source is None:
            await get_from_telegram_server()
        elif isinstance(source, asyncio.Queue):
            if ordered:
                await get_from_queue(source)
            else:
                await get_from_queue_unordered(source)
        else:
            raise ValueError('Invalid source')


class SpeakerBot(Bot):
    def __init__(self, token, loop=None):
        super(SpeakerBot, self).__init__(token, loop)
        self._mic = helper.Microphone()

    @property
    def mic(self):
        return self._mic

    def create_listener(self):
        q = asyncio.Queue()
        self._mic.add(q)
        ln = helper.Listener(self._mic, q)
        return ln


class DelegatorBot(SpeakerBot):
    def __init__(self, token, delegation_patterns, loop=None):
        """
        :param delegation_patterns: a list of (seeder, delegator) tuples.
        """
        super(DelegatorBot, self).__init__(token, loop)
        self._delegate_records = [p+({},) for p in delegation_patterns]

    def handle(self, msg):
        self._mic.send(msg)

        for calculate_seed, make_coroutine_obj, dict in self._delegate_records:
            id = calculate_seed(msg)

            if id is None:
                continue
            elif isinstance(id, collections.Hashable):
                if id not in dict or dict[id].done():
                    c = make_coroutine_obj((self, msg, id))

                    if not asyncio.iscoroutine(c):
                        raise RuntimeError('You must produce a coroutine *object* as delegate.')

                    dict[id] = self._loop.create_task(c)
            else:
                c = make_coroutine_obj((self, msg, id))
                self._loop.create_task(c)
