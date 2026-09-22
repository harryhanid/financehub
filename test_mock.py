current_content = "initial"
class MockFile:
    def __init__(self, content): self.content = content.replace("\r\n", "\n")
    def read(self): return self.content
    def write(self, s):
        global current_content
        current_content = s.replace("\r\n", "\n")
    def __enter__(self): return self
    def __exit__(self, *a): pass

m = MockFile(current_content)
m.write("new content")
print(current_content)
