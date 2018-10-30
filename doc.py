def renderObject(docs):
    if type(docs) == 'list':
      for doc in docs:
        return doc
    elif type(docs) == 'dict':
      for doc in docs:
        return doc
    else:
      return docs
 
