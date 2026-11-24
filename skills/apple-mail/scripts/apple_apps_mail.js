function run(argv) {
  var action = argv.length > 0 ? String(argv[0]) : "";
  var payload = {};
  if (argv.length > 1 && argv[1]) {
    payload = JSON.parse(String(argv[1]));
  }

  var app = Application("Mail");
  app.includeStandardAdditions = true;

  try {
    switch (action) {
      case "accounts":
        return JSON.stringify(listAccounts(app));
      case "mailboxes":
        return JSON.stringify(listMailboxes(app, payload));
      case "recent":
        return JSON.stringify(recentMessages(app, payload));
      case "search":
        return JSON.stringify(searchMessages(app, payload));
      case "read":
        return JSON.stringify(readMessage(app, payload));
      case "mark":
        return JSON.stringify(markMessage(app, payload));
      case "move":
        return JSON.stringify(moveMessage(app, payload));
      case "archive":
        return JSON.stringify(archiveMessage(app, payload));
      case "delete":
        return JSON.stringify(deleteMessage(app, payload));
      case "triageMeta":
        return JSON.stringify(triageMetaMessages(app, payload));
      case "batchHeaders":
        return JSON.stringify(batchMessageDetails(app, payload, false));
      case "batchBodies":
        return JSON.stringify(batchMessageDetails(app, payload, true));
      default:
        throw new Error("unsupported action: " + action);
    }
  } catch (error) {
    throw new Error(String(error.message || error));
  }
}

function listAccounts(app) {
  return app.accounts().map(function (account) {
    return {
      id: safeCall(function () { return String(account.id()); }, null),
      name: String(account.name()),
      accountType: safeCall(function () { return String(account.class()); }, null),
    };
  });
}

function listMailboxes(app, payload) {
  var account = requireAccount(app, payload.account);
  var results = [];
  walkMailboxes(account.mailboxes(), "", String(account.name()), results);
  return results;
}

function recentMessages(app, payload) {
  var limit = clampInt(payload.limit, 20, 1, 200);
  var maxScanPerBox = clampInt(payload.maxScanPerBox, Math.max(limit + 2, 5), 1, 2000);
  var includeRead = truthy(payload.includeRead);
  if (!normalize(payload.account) && !normalize(payload.mailbox) && !normalize(payload.mailboxPath)) {
    var fastOut = [];
    forEach(app.accounts(), function (account) {
      var inboxEntry = resolveDefaultInboxMailbox(account);
      if (!inboxEntry) {
        return;
      }
      scanMailboxMessages(inboxEntry.mailbox, maxScanPerBox, function (message) {
        var fastItem = summarizeListMessage(message, String(account.name()), inboxEntry.path);
        if (!includeRead && fastItem.read) {
          return;
        }
        fastOut.push(fastItem);
      });
    });
    fastOut.sort(compareByDateDesc);
    return fastOut.slice(0, limit);
  }

  var mailboxes = resolveSourceMailboxes(app, payload);
  var out = [];

  forEach(mailboxes, function (entry) {
    scanMailboxMessages(entry.mailbox, maxScanPerBox, function (message) {
      var item = summarizeListMessage(message, entry.accountName, entry.path);
      if (!includeRead && item.read) {
        return;
      }
      out.push(item);
    });
  });

  out.sort(compareByDateDesc);
  return out.slice(0, limit);
}

function searchMessages(app, payload) {
  var query = normalize(payload.query).toLowerCase();
  var limit = clampInt(payload.limit, 20, 1, 200);
  var maxScanPerBox = clampInt(payload.maxScanPerBox, Math.max(limit * 4, 20), 1, 4000);
  var includeBody = truthy(payload.includeBody);
  var includeRead = truthy(payload.includeRead);
  if (!normalize(payload.account) && !normalize(payload.mailbox) && !normalize(payload.mailboxPath)) {
    var fastOut = [];
    forEach(app.accounts(), function (account) {
      var inboxEntry = resolveDefaultInboxMailbox(account);
      if (!inboxEntry) {
        return;
      }
      scanMailboxMessages(inboxEntry.mailbox, maxScanPerBox, function (message) {
        var fastItem = summarizeListMessage(message, String(account.name()), inboxEntry.path);
        if (!includeRead && fastItem.read) {
          return;
        }
        if (query && !messageMatches(message, query, includeBody)) {
          return;
        }
        fastOut.push(fastItem);
      });
    });
    fastOut.sort(compareByDateDesc);
    return fastOut.slice(0, limit);
  }

  var mailboxes = resolveSourceMailboxes(app, payload);
  var out = [];

  forEach(mailboxes, function (entry) {
    scanMailboxMessages(entry.mailbox, maxScanPerBox, function (message) {
      var item = summarizeListMessage(message, entry.accountName, entry.path);
      if (!includeRead && item.read) {
        return;
      }
      if (query && !messageMatches(message, query, includeBody)) {
        return;
      }
      out.push(item);
    });
  });

  out.sort(compareByDateDesc);
  return out.slice(0, limit);
}

function readMessage(app, payload) {
  var located = locateMessageValue(app, payload);
  var message = located.message;
  return {
    id: safeCall(function () { return message.id(); }, null),
    messageId: safeCall(function () { return String(message.messageId()); }, null),
    subject: safeCall(function () { return String(message.subject()); }, ""),
    sender: safeCall(function () { return String(message.sender()); }, ""),
    read: safeCall(function () { return !!message.readStatus(); }, false),
    flagged: safeCall(function () { return !!message.flaggedStatus(); }, false),
    dateReceived: toIso(safeCall(function () { return message.dateReceived(); }, null)),
    dateSent: toIso(safeCall(function () { return message.dateSent(); }, null)),
    account: located.accountName,
    mailbox: located.mailboxName,
    mailboxPath: located.mailboxPath,
    content: safeCall(function () { return String(message.content()); }, ""),
    allHeaders: safeCall(function () { return String(message.allHeaders()); }, ""),
  };
}

function markMessage(app, payload) {
  var located = locateMessageValue(app, payload);
  var message = located.message;
  if (payload.read === undefined && payload.flagged === undefined) {
    throw new Error("mark requires --read and/or --flagged");
  }
  if (payload.read !== undefined) {
    message.readStatus = truthy(payload.read);
  }
  if (payload.flagged !== undefined) {
    message.flaggedStatus = truthy(payload.flagged);
  }
  return {
    ok: true,
    id: safeCall(function () { return message.id(); }, null),
    account: located.accountName,
    mailbox: located.mailboxName,
    mailboxPath: located.mailboxPath,
    read: safeCall(function () { return !!message.readStatus(); }, false),
    flagged: safeCall(function () { return !!message.flaggedStatus(); }, false),
  };
}

function moveMessage(app, payload) {
  var source = locateMessageSpecifier(app, payload);
  var destinationAccountName = normalize(payload.toAccount) || source.accountName;
  var destinationAccount = requireAccount(app, destinationAccountName);
  var destination = requireMailbox(destinationAccount, {
    mailbox: payload.toMailbox,
    mailboxPath: payload.toMailboxPath,
  });

  app.move(source.specifier, { to: destination.mailbox });
  return {
    ok: true,
    id: source.id,
    account: source.accountName,
    mailbox: source.mailboxName,
    mailboxPath: source.mailboxPath,
    toAccount: String(destinationAccount.name()),
    toMailbox: destination.mailboxName,
    toMailboxPath: destination.path,
  };
}

function archiveMessage(app, payload) {
  var source = locateMessageSpecifier(app, payload);
  var account = requireAccount(app, source.accountName);
  var destination = resolveArchiveMailbox(account, payload.archiveMailbox, payload.archiveMailboxPath);
  if (!destination) {
    throw new Error("archive mailbox not found for account: " + source.accountName);
  }

  app.move(source.specifier, { to: destination.mailbox });
  return {
    ok: true,
    id: source.id,
    account: source.accountName,
    mailbox: source.mailboxName,
    mailboxPath: source.mailboxPath,
    toAccount: source.accountName,
    toMailbox: destination.mailboxName,
    toMailboxPath: destination.path,
  };
}

function deleteMessage(app, payload) {
  var source = locateMessageSpecifier(app, payload);
  app.delete(source.specifier);
  return {
    ok: true,
    id: source.id,
    account: source.accountName,
    mailbox: source.mailboxName,
    mailboxPath: source.mailboxPath,
  };
}

function triageMetaMessages(app, payload) {
  var info = locateMailboxContext(app, payload);
  var limit = clampInt(payload.limit, 20, 1, 2000);
  var out = [];
  scanMailboxMessages(info.mailbox, limit, function (message) {
    out.push({
      id: safeCall(function () { return message.id(); }, null),
      messageId: safeCall(function () { return String(message.messageId()); }, null),
      subject: safeCall(function () { return String(message.subject()); }, ""),
      sender: safeCall(function () { return String(message.sender()); }, ""),
      read: safeCall(function () { return !!message.readStatus(); }, false),
      mailbox: info.mailboxName,
      mailboxPath: info.mailboxPath,
      account: info.accountName,
      allHeaders: safeCall(function () { return String(message.allHeaders()); }, ""),
    });
  });
  return out;
}

function batchMessageDetails(app, payload, includeContent) {
  var info = locateMailboxContext(app, payload);
  var ids = Array.isArray(payload.ids) ? payload.ids : [];
  var out = [];
  for (var i = 0; i < ids.length; i++) {
    var numericId = Number(ids[i]);
    if (!isFinite(numericId)) {
      continue;
    }
    var item = safeCall(function () {
      var message = info.mailbox.messages.byId(numericId);
      var entry = {
        id: message.id(),
        allHeaders: String(message.allHeaders()),
      };
      if (includeContent) {
        entry.content = String(message.content());
      }
      return entry;
    }, null);
    if (item) {
      out.push(item);
    }
  }
  return out;
}

function requireAccount(app, accountName) {
  var wanted = normalize(accountName);
  if (!wanted) {
    throw new Error("account is required");
  }
  var accounts = app.accounts();
  for (var i = 0; i < accounts.length; i++) {
    var account = accounts[i];
    var name = String(account.name());
    var id = safeCall(function () { return String(account.id()); }, "");
    if (name === wanted || id === wanted) {
      return account;
    }
  }
  throw new Error("account not found: " + wanted);
}

function requireMailbox(account, spec) {
  var candidates = [];
  var wantedName = normalize(spec.mailbox);
  var wantedPath = normalize(spec.mailboxPath);
  walkMailboxes(account.mailboxes(), "", String(account.name()), candidates);
  var matches = candidates.filter(function (item) {
    if (wantedPath) {
      return item.path === wantedPath;
    }
    return wantedName && item.name === wantedName;
  });

  if (!matches.length) {
    throw new Error(
      "mailbox not found on account " +
        String(account.name()) +
        ": " +
        (wantedPath || wantedName || "<empty>")
    );
  }
  if (!wantedPath && matches.length > 1) {
    throw new Error(
      "mailbox name is ambiguous on account " +
        String(account.name()) +
        ": " +
        wantedName +
        " (pass mailboxPath instead)"
    );
  }
  return matches[0];
}

function resolveArchiveMailbox(account, archiveMailbox, archiveMailboxPath) {
  var all = [];
  walkMailboxes(account.mailboxes(), "", String(account.name()), all);
  var explicitPath = normalize(archiveMailboxPath);
  var explicitName = normalize(archiveMailbox);
  if (explicitPath || explicitName) {
    var explicit = all.filter(function (item) {
      return explicitPath ? item.path === explicitPath : item.name === explicitName;
    });
    return explicit.length ? explicit[0] : null;
  }

  var wantedNames = ["Archive", "Archives", "All Mail", "归档", "存档", "已归档"];
  for (var i = 0; i < wantedNames.length; i++) {
    for (var j = 0; j < all.length; j++) {
      if (all[j].name === wantedNames[i]) {
        return all[j];
      }
    }
  }
  return null;
}

function resolveSourceMailboxes(app, payload) {
  var accountName = normalize(payload.account);
  var mailboxName = normalize(payload.mailbox);
  var mailboxPath = normalize(payload.mailboxPath);

  if (accountName && (mailboxName || mailboxPath)) {
    var account = requireAccount(app, accountName);
    return [requireMailbox(account, payload)];
  }

  if (accountName) {
    var singleAccount = requireAccount(app, accountName);
    var defaultInbox = resolveDefaultInboxMailbox(singleAccount);
    if (defaultInbox) {
      return [defaultInbox];
    }
  }

  var accounts = app.accounts();
  var out = [];
  forEach(accounts, function (account) {
    var mailboxes = [];
    walkMailboxes(account.mailboxes(), "", String(account.name()), mailboxes);
    var inboxes = mailboxes.filter(function (item) {
      return looksLikeInbox(item.name, item.path);
    });
    if (!inboxes.length) {
      out = out.concat(mailboxes.slice(0, 1));
    } else {
      out = out.concat(inboxes);
    }
  });
  return out;
}

function locateMessageValue(app, payload) {
  var info = locateMailboxContext(app, payload);
  var wantedId = normalize(payload.id);
  var wantedMessageId = normalize(payload.messageId);
  if (wantedId) {
    var numericId = Number(wantedId);
    if (isFinite(numericId)) {
      var direct = safeCall(function () { return info.mailbox.messages.byId(numericId); }, null);
      var directSubject = safeCall(function () { return String(direct.subject()); }, "");
      if (direct && directSubject !== "") {
        return {
          message: direct,
          accountName: info.accountName,
          mailboxName: info.mailboxName,
          mailboxPath: info.mailboxPath,
        };
      }
    }
  }

  var found = null;
  scanMailboxMessages(info.mailbox, clampInt(payload.maxLocateScan, 200, 1, 5000), function (message) {
    var candidateId = String(safeCall(function () { return message.id(); }, ""));
    var candidateMessageId = String(safeCall(function () { return message.messageId(); }, ""));
    if ((wantedId && candidateId === wantedId) || (wantedMessageId && candidateMessageId === wantedMessageId)) {
      found = {
        message: message,
        accountName: info.accountName,
        mailboxName: info.mailboxName,
        mailboxPath: info.mailboxPath,
      };
    }
  });
  if (found) {
    return found;
  }
  throw new Error("message not found in mailbox: " + info.mailboxPath);
}

function locateMessageSpecifier(app, payload) {
  var info = locateMailboxContext(app, payload);
  var wantedId = normalize(payload.id);
  if (!wantedId) {
    throw new Error("id is required for mutating commands");
  }
  var numericId = Number(wantedId);
  if (!isFinite(numericId)) {
    throw new Error("id must be a numeric Mail message id");
  }
  return {
    specifier: info.mailbox.messages.byId(numericId),
    id: numericId,
    accountName: info.accountName,
    mailboxName: info.mailboxName,
    mailboxPath: info.mailboxPath,
  };
}

function locateMailboxContext(app, payload) {
  var account = requireAccount(app, payload.account);
  var mailbox = requireMailbox(account, payload);
  return {
    mailbox: mailbox.mailbox,
    accountName: String(account.name()),
    mailboxName: mailbox.name,
    mailboxPath: mailbox.path,
  };
}

function walkMailboxes(mailboxes, prefix, accountName, out) {
  forEach(mailboxes, function (mailbox) {
    var name = String(mailbox.name());
    var path = prefix ? prefix + "/" + name : name;
    out.push({
      account: accountName,
      name: name,
      path: path,
      unreadCount: safeCall(function () { return mailbox.unreadCount(); }, null),
      mailbox: mailbox,
    });
    walkMailboxes(safeCall(function () { return mailbox.mailboxes(); }, []), path, accountName, out);
  });
}

function resolveDefaultInboxMailbox(account) {
  var candidates = ["INBOX", "Inbox", "收件箱", "收件匣"];
  for (var i = 0; i < candidates.length; i++) {
    var name = candidates[i];
    var mailbox = safeCall(function () { return account.mailboxes.byName(name); }, null);
    var resolved = safeCall(function () { return String(mailbox.name()); }, "");
    if (resolved) {
      return {
        account: String(account.name()),
        name: resolved,
        path: resolved,
        mailbox: mailbox,
      };
    }
  }

  var fallback = [];
  walkMailboxes(account.mailboxes(), "", String(account.name()), fallback);
  for (var j = 0; j < fallback.length; j++) {
    if (looksLikeInbox(fallback[j].name, fallback[j].path)) {
      return fallback[j];
    }
  }
  return null;
}

function scanMailboxMessages(mailbox, limit, fn) {
  for (var i = 0; i < limit; i++) {
    var message = safeCall(function () { return mailbox.messages[i]; }, null);
    if (!message) {
      break;
    }
    var id = safeCall(function () { return message.id(); }, null);
    if (id === null || id === undefined) {
      break;
    }
    fn(message, i);
  }
}

function summarizeMessage(message, accountName, mailboxPath) {
  var derivedMailboxPath = mailboxPath || safeCall(function () { return String(message.mailbox().name()); }, "");
  var derivedAccountName =
    accountName ||
    safeCall(function () { return String(message.mailbox().container().name()); }, "");
  var subject = safeCall(function () { return String(message.subject()); }, "");
  var sender = safeCall(function () { return String(message.sender()); }, "");
  var content = safeCall(function () { return String(message.content()); }, "");
  return {
    id: safeCall(function () { return message.id(); }, null),
    messageId: safeCall(function () { return String(message.messageId()); }, null),
    subject: subject,
    sender: sender,
    read: safeCall(function () { return !!message.readStatus(); }, false),
    flagged: safeCall(function () { return !!message.flaggedStatus(); }, false),
    dateReceived: toIso(safeCall(function () { return message.dateReceived(); }, null)),
    dateSent: toIso(safeCall(function () { return message.dateSent(); }, null)),
    account: derivedAccountName,
    mailbox: basename(derivedMailboxPath),
    mailboxPath: derivedMailboxPath,
    preview: previewText(content, 160),
  };
}

function summarizeListMessage(message, accountName, mailboxPath) {
  var derivedMailboxPath = mailboxPath || safeCall(function () { return String(message.mailbox().name()); }, "");
  var derivedAccountName =
    accountName ||
    safeCall(function () { return String(message.mailbox().container().name()); }, "");
  return {
    id: safeCall(function () { return message.id(); }, null),
    messageId: safeCall(function () { return String(message.messageId()); }, null),
    subject: safeCall(function () { return String(message.subject()); }, ""),
    sender: safeCall(function () { return String(message.sender()); }, ""),
    read: safeCall(function () { return !!message.readStatus(); }, false),
    flagged: safeCall(function () { return !!message.flaggedStatus(); }, false),
    dateReceived: toIso(safeCall(function () { return message.dateReceived(); }, null)),
    dateSent: toIso(safeCall(function () { return message.dateSent(); }, null)),
    account: derivedAccountName,
    mailbox: basename(derivedMailboxPath),
    mailboxPath: derivedMailboxPath,
  };
}

function messageMatches(message, query, includeBody) {
  var fields = [
    safeCall(function () { return String(message.subject()); }, ""),
    safeCall(function () { return String(message.sender()); }, ""),
  ];
  if (includeBody) {
    fields.push(safeCall(function () { return String(message.content()); }, ""));
  }
  for (var i = 0; i < fields.length; i++) {
    if (fields[i].toLowerCase().indexOf(query) !== -1) {
      return true;
    }
  }
  return false;
}

function looksLikeInbox(name, path) {
  var value = normalize(name).toLowerCase();
  if (value === "inbox" || value === "收件箱" || value === "收件匣") {
    return true;
  }
  var full = normalize(path).toLowerCase();
  return full.indexOf("/inbox") !== -1 || full === "inbox";
}

function compareByDateDesc(left, right) {
  var leftValue = left.dateReceived || left.dateSent || "";
  var rightValue = right.dateReceived || right.dateSent || "";
  if (leftValue === rightValue) {
    return 0;
  }
  return leftValue < rightValue ? 1 : -1;
}

function basename(path) {
  var parts = normalize(path).split("/");
  return parts.length ? parts[parts.length - 1] : "";
}

function clampInt(value, fallback, minimum, maximum) {
  var numeric = parseInt(value, 10);
  if (!isFinite(numeric)) {
    numeric = fallback;
  }
  if (numeric < minimum) {
    numeric = minimum;
  }
  if (numeric > maximum) {
    numeric = maximum;
  }
  return numeric;
}

function truthy(value) {
  if (typeof value === "boolean") {
    return value;
  }
  var text = normalize(value).toLowerCase();
  return text === "1" || text === "true" || text === "yes" || text === "y" || text === "on";
}

function normalize(value) {
  if (value === undefined || value === null) {
    return "";
  }
  return String(value).trim();
}

function toIso(value) {
  if (!value) {
    return null;
  }
  return new Date(value).toISOString();
}

function safeCall(fn, fallback) {
  try {
    return fn();
  } catch (error) {
    return fallback;
  }
}

function forEach(list, fn) {
  for (var i = 0; i < list.length; i++) {
    fn(list[i], i);
  }
}
