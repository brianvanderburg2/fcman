// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_ACTIONS_H
#define __FCMAN_ACTIONS_H


// Requirements
#include <wx/defs.h>
#include <wx/string.h>

#include "collection/collection.h"


class WXDLLIMPEXP_CORE wxWindow;
class WXDLLIMPEXP_CORE wxProgressDialog;

class Log;


// A callback used by the actions
class ActionCallback
{
public:
    // ctor/dtor
    ActionCallback(wxWindow* parent, Log* m_log, const wxString& title);
    virtual ~ActionCallback();

    // Information
    wxWindow* GetParent() { return m_parent; }

    // Update the callback
    bool Progress(const wxString& message);
    void LogMessage(const wxString& message, bool important = false);

    // Set the skip period for updating progress message
    void SetProgressSkip(int skip = 0);

    // Suspend/resume the callback
    void Suspend();
    void Resume();

private:
    wxWindow* m_parent;
    Log* m_log;
    wxString m_title;
    wxProgressDialog* m_progress;

    bool m_continue;
    int m_skip;
    int m_counter;
};


// Scan for and report missing, extra, duplicate and wrong size items and dependencies
bool VerifySanity(Directory* dir, ActionCallback& callback);

// Add for new items
bool AddNewItems(Directory* dir, ActionCallback& callback);

// Rename missing items
bool RenameMissingItems(Directory* dir, ActionCallback& callback);

// Remove missing items
bool RemoveMissingItems(Directory* dir, ActionCallback& callback);

// Calculate checksums
bool CalculateChecksums(const FileList& files, ActionCallback& callback, const wxString& type, bool all = true);
bool CalculateChecksums(Directory* dir, ActionCallback& callback, const wxString& type, bool all = true);

// Verify checksums
bool VerifyChecksums(const FileList& files, ActionCallback& callback);
bool VerifyChecksums(Directory* dir, ActionCallback& callback);

// Mark dirty or clean
bool MarkDirty(const FileList& files, ActionCallback& callback, bool dirty);

#endif // Header guard



