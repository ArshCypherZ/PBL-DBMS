# Basic test cases
# Established by: All Members

import sys
sys.path.append('../backend')
from nlp_parser import NLPParser

def test_select():
    parser = NLPParser()
    result = parser.parse("show all users")
    assert result['operation'] == 'select'
    print("SELECT test passed")

def test_insert():
    parser = NLPParser()
    result = parser.parse("add user name: Test User email: test@example.com")
    assert result['operation'] == 'insert'
    assert result['params'][0] == 'Test User'
    print("INSERT test passed")

def test_update():
    parser = NLPParser()
    result = parser.parse("update user id: 1 name: Updated email: updated@example.com")
    assert result['operation'] == 'update'
    assert result['params'][0] == 1
    print("UPDATE test passed")

if __name__ == "__main__":
    test_select()
    test_insert()
    test_update()
    print("\nAll tests passed!")
