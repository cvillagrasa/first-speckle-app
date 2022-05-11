def commit_url(stream, commit) -> str:
    return f'https://speckle.xyz/embed?stream={stream.id}&commit={commit.id}'


def list_to_markdown(lst: list) -> str:
    return ''.join([f'- {element} \n' for element in lst])
