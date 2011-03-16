// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_COLLECTION_COLLECTION_H
#define __FCMAN_COLLECTION_COLLECTION_H


// Requirements
#include <wx/defs.h>
#include <wx/string.h>

#include "node.h"
#include "file.h"
#include "dir.h"
#include "version.h"
#include "package.h"
#include "depends.h"


class WXDLLIMPEXP_XML wxXmlNode;


// Collection class
class Collection : public Directory
{
public:
    // dtor (ctor is private)
    virtual ~Collection();

    // Information
    const wxString& GetFilename() const { return m_filename; }
    const wxString& GetBackupFilename() const { return m_backup; }

    // New/open
    static Collection* New(const wxString& filename);
    static Collection* Open(const wxString& collection);

    wxXmlNode* Save();
    bool SaveFile(bool backup=true);

    // Base operations
    bool CanDelete();
    bool CanRename(const wxString& name);
    bool CanMove(Directory* parent);
    void Reset();

    // Dirty or not
    void SetDirty(bool dirty = true) { m_dirty = dirty; }
    bool IsDirty() const { return m_dirty; }

    // Close
    void Close();

private:
    // ctor
    Collection(const wxString& filename, wxXmlNode* node = NULL);

    // No copy/assign
    Collection(const Collection& copy);
    Collection& operator=(const Collection& rhs);

    // Information
    wxString m_filename;
    wxString m_backup;
    bool m_dirty;
};



#endif // Header guard



