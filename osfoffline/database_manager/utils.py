
def save(session, item=None):
    if item:
        session.add(item)
    try:
        session.commit()
    except:
        session.rollback()
        raise