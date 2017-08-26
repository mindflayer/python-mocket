import requests
from sure import expect

from mocket import httpretty


@httpretty.activate
def test_yipit_api_returning_deals():
    httpretty.register_uri(httpretty.GET, "http://api.yipit.com/v1/deals/",
                           body='[{"title": "Test Deal"}]',
                           content_type="application/json")

    response = requests.get('http://api.yipit.com/v1/deals/')

    expect(response.json()).to.equal([{"title": "Test Deal"}])


def test_one():
    httpretty.enable()  # enable HTTPretty so that it will monkey patch the socket module
    httpretty.register_uri(httpretty.GET, "http://yipit.com/",
                           body="Find the best daily deals")

    response = requests.get('http://yipit.com')

    assert response.text == "Find the best daily deals"

    httpretty.disable()  # disable afterwards, so that you will have no problems in code that uses that socket module
    httpretty.reset()    # reset HTTPretty state (clean up registered urls and request history)


# def test_two():  # test_one again in the README of httpretty
#     httpretty.enable()  # enable HTTPretty so that it will monkey patch the socket module
#     httpretty.register_uri(httpretty.GET, "http://yipit.com/login",
#                            body="Find the best daily deals")
#
#     requests.get('http://yipit.com/login?email=user@github.com&password=foobar123')
#     expect(httpretty.last_request()).to.have.property("querystring").being.equal({
#         "email": "user@github.com",
#         "password": "foobar123",
#     })
#
#     httpretty.disable()  # disable afterwards, so that you will have no problems in code that uses that socket module


@httpretty.activate
def test_three():  # test_one again in the README of httpretty
    httpretty.register_uri(httpretty.GET, "http://yipit.com/",
                           body="Find the best daily deals")

    response = requests.get('http://yipit.com')
    assert response.text == "Find the best daily deals"


@httpretty.activate
def test_github_access():
    httpretty.register_uri(httpretty.GET, "http://github.com/",
                           body="here is the mocked body",
                           status=201)

    response = requests.get('http://github.com')
    expect(response.status_code).to.equal(201)


@httpretty.activate
def test_some_api():
    httpretty.register_uri(httpretty.GET, "http://foo-api.com/gabrielfalcao",
                           body='{"success": false}',
                           status=500,
                           content_type='text/json')

    response = requests.get('http://foo-api.com/gabrielfalcao')

    expect(response.json()).to.equal({'success': False})
    expect(response.status_code).to.equal(500)


@httpretty.activate
def test_some_api_two():  # test_some_api again in the README of httpretty
    httpretty.register_uri(httpretty.GET, "http://foo-api.com/gabrielfalcao",
                           body='{"success": false}',
                           status=500,
                           content_type='text/json',
                           adding_headers={
                               'X-foo': 'bar'
                           })

    response = requests.get('http://foo-api.com/gabrielfalcao')

    expect(response.json()).to.equal({'success': False})
    expect(response.status_code).to.equal(500)


@httpretty.activate
def test_rotating_responses():
    httpretty.register_uri(httpretty.GET, "http://github.com/gabrielfalcao/httpretty",
                           responses=[
                               httpretty.Response(body="first response", status=201),
                               httpretty.Response(body='second and last response', status=202),
                            ])

    response1 = requests.get('http://github.com/gabrielfalcao/httpretty')
    expect(response1.status_code).to.equal(201)
    expect(response1.text).to.equal('first response')

    response2 = requests.get('http://github.com/gabrielfalcao/httpretty')
    expect(response2.status_code).to.equal(202)
    expect(response2.text).to.equal('second and last response')

    response3 = requests.get('http://github.com/gabrielfalcao/httpretty')

    expect(response3.status_code).to.equal(202)
    expect(response3.text).to.equal('second and last response')


# # mock a streaming response body with a generator
# def mock_streaming_tweets(tweets):
#     from time import sleep
#     for t in tweets:
#         sleep(.5)
#         yield t
#
#
# @httpretty.activate
# def test_twitter_api_integration():
#     twitter_response_lines = [
#         '{"text":"If @BarackObama requests to follow me one more time I\'m calling the police."}\r\n',
#         '\r\n',
#         '{"text":"Thanks for all your #FollowMe1D requests Directioners! We\u2019ll be following 10 people throughout the day starting NOW. G ..."}\r\n'
#     ]
#
#     TWITTER_STREAMING_URL = "https://stream.twitter.com/1/statuses/filter.json"
#
#     # set the body to a generator and set `streaming=True` to mock a streaming response body
#     httpretty.register_uri(httpretty.POST, TWITTER_STREAMING_URL,
#                            body=mock_streaming_tweets(twitter_response_lines),
#                            streaming=True)
#
#     # taken from the requests docs
#     # http://docs.python-requests.org/en/latest/user/advanced/#streaming-requests
#     response = requests.post(TWITTER_STREAMING_URL, data={'track':'requests'},
#                             auth=('username','password'), prefetch=False)
#
#     # test iterating by line
#     line_iter = response.iter_lines()
#     for i in range(len(twitter_response_lines)):
#         expect(line_iter.next().strip()).to.equal(twitter_response_lines[i].strip())


# @httpretty.activate
# def test_httpretty_should_allow_registering_regexes():
#     u"HTTPretty should allow registering regexes"
#
#     httpretty.register_uri(
#         httpretty.GET,
#         re.compile("api.yipit.com/v2/deal;brand=(\w+)"),
#         body="Found brand",
#     )
#
#     response = requests.get('https://api.yipit.com/v2/deal;brand=GAP')
#     expect(response.text).to.equal('Found brand')
#     expect(httpretty.last_request().method).to.equal('GET')
#     expect(httpretty.last_request().path).to.equal('/v1/deal;brand=GAP')


@httpretty.activate
def test_yipit_api_integration():
    httpretty.register_uri(httpretty.POST, "http://api.yipit.com/foo/",
                           body='{"repositories": ["HTTPretty", "lettuce"]}')

    response = requests.post('http://api.yipit.com/foo',
                             '{"username": "gabrielfalcao"}',
                             headers={
                                 'content-type': 'text/json',
                             })

    expect(response.text).to.equal('{"repositories": ["HTTPretty", "lettuce"]}')
    expect(httpretty.last_request().method).to.equal("POST")
    expect(httpretty.last_request().headers['content-type']).to.equal('text/json')
