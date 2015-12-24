from tooler import (
  Tooler,
  bash,
  bash_quote,
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
    proceed_or_abort('Are you sure you want to upload the photo?')

  bash('echo Uploading photo: %s' % bash_quote(arguments['<photo>']))

if __name__ == '__main__':
  tooler.run()

