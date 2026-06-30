import Foundation

func isUserCancelledFileDialog(_ error: Error) -> Bool {
    if error is CancellationError {
        return true
    }

    let nsError = error as NSError
    return nsError.domain == NSCocoaErrorDomain
        && nsError.code == CocoaError.Code.userCancelled.rawValue
}

func isUserCancelledFileExport(_ error: Error) -> Bool {
    isUserCancelledFileDialog(error)
}
