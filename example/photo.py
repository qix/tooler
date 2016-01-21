from tooler import (
  Tooler,
  bash,
  bash_quote,
  env,
  proceed_or_abort,
)

tooler = Tooler()

@tooler.command(docopt=True)
def upload(arguments):
  """
Usage: upload <photo> [options]

  --skip-confirm      skip confirmation
"""
  if not arguments['--skip-confirm']:
    proceed_or_abort('Are you sure you want to upload the photo?', default=True)

  bash('echo Uploading photo: %s' % bash_quote(arguments['<photo>']))

  with env.settings(hosts=['23.236.62.211']):
    bash('echo Restarting server')

if __name__ == '__main__':
  tooler.run()
