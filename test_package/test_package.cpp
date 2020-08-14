#include <cstdlib>
#include <Corrade/Utility/Debug.h>
#include <Corrade/Containers/Array.h>

int main() {
    Corrade::Utility::Debug{} << Corrade::Containers::Array<int>{5};
    Corrade::Utility::Debug{} << "Success";

    return EXIT_SUCCESS;
}
