// These declarations can all be reformatted
class Declaration;
    class Declaration;

// Empty classes should also be reformatted
class Empty {};

// The following should also not be skipped (even though it is not in line with Haiku style
class Empty{}
;

// The following should be picked up as a class, with line 14 being skipped
class Class {
    int i;
};

// The following should be picked up as class, lines 19, 20 and 21
class Class
{
    int i;
    int j;
}
;

// The following is valid C++, but the simple parser will not pick it up because it matches on the keyword plus a space
class
Class{};

// The following is valid C++, but our simple parser will not pick it up
class Class

{
    int i;
};

// The following test validates whether the parser keeps track of the levels of parenthesis, lines 38-47
class NestedBlocks {
public:
    NestedBlocks() {}
    bool IsNested() {
        if (true) {
            function_call();
            int i = {
                0
            };
        }
    }
};

// Double check struct declarations and definitions too. Line 53 and 54 should be parsed.
struct SkippedDeclaration;
struct Struct : public Class {
    int i;
    int j;
};
