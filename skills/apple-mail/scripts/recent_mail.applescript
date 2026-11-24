on sanitizeText(valueText)
    set sourceText to valueText as text
    set oldTids to AppleScript's text item delimiters
    set AppleScript's text item delimiters to {return, linefeed, tab}
    set parts to text items of sourceText
    set AppleScript's text item delimiters to " "
    set cleanedText to parts as text
    set AppleScript's text item delimiters to oldTids
    return cleanedText
end sanitizeText

on pad2(n)
    set textValue to n as text
    if (length of textValue) is 1 then
        return "0" & textValue
    end if
    return textValue
end pad2

on isoLocalDate(d)
    if d is missing value then
        return ""
    end if
    set yyyy to year of d as integer
    set mm to month of d as integer
    set dd to day of d as integer
    set hh to hours of d as integer
    set mins to minutes of d as integer
    set ss to seconds of d as integer
    return (yyyy as text) & "-" & my pad2(mm) & "-" & my pad2(dd) & "T" & my pad2(hh) & ":" & my pad2(mins) & ":" & my pad2(ss)
end isoLocalDate

on run argv
    set accountName to item 1 of argv
    set mailboxName to item 2 of argv
    set requestedLimit to (item 3 of argv) as integer
    set startIndex to 1
    if (count of argv) >= 4 then
        set startIndex to (item 4 of argv) as integer
    end if
    if startIndex < 1 then
        set startIndex to 1
    end if

    tell application "Mail"
        tell mailbox mailboxName of account accountName
            set totalCount to count of messages
            if totalCount is 0 or startIndex > totalCount then
                return ""
            end if
            set endIndex to (startIndex + requestedLimit - 1)
            if endIndex > totalCount then
                set endIndex to totalCount
            end if
            set messageIds to (get id of messages startIndex thru endIndex)
            set internetMessageIds to (get message id of messages startIndex thru endIndex)
            set subjects to (get subject of messages startIndex thru endIndex)
            set senders to (get sender of messages startIndex thru endIndex)
            set readStatuses to (get read status of messages startIndex thru endIndex)
            set receivedDates to (get date received of messages startIndex thru endIndex)
            set sentDates to (get date sent of messages startIndex thru endIndex)
            set rows to {}
            set rowCount to (endIndex - startIndex + 1)
            repeat with i from 1 to rowCount
                set end of rows to ((item i of messageIds as text) & tab & my sanitizeText(item i of internetMessageIds) & tab & my sanitizeText(item i of subjects) & tab & my sanitizeText(item i of senders) & tab & (item i of readStatuses as text) & tab & mailboxName & tab & accountName & tab & my isoLocalDate(item i of receivedDates) & tab & my isoLocalDate(item i of sentDates))
            end repeat
        end tell
    end tell

    set oldTids to AppleScript's text item delimiters
    set AppleScript's text item delimiters to linefeed
    set outputText to rows as text
    set AppleScript's text item delimiters to oldTids
    return outputText
end run
