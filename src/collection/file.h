// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_FILE_NODE_H
#define __FCMAN_FILE_NODE_H


// Requirements
#include <list>

#include <wx/defs.h>
#include <wx/string.h>

#include "node.h"
#include "package.h"
#include "depends.h"


// File class
class File;
typedef std::list<File*> FileList;

class File : public Node
{
public:
    // ctor/dtor
    File();
    File(wxXmlNode* node);

    virtual ~File();

    // Save to an XML node
    virtual wxXmlNode* Save();

    // Actions
    virtual bool Exists() const;

    // Checksum
    void SetChecksum(const wxString& checksum);
    const wxString& GetChecksum() const { return m_checksum; }
    
    // Size
    void SetSize(wxULongLong_t size);
    wxULongLong_t GetSize() const { return m_size; }
    wxULongLong_t GetRealSize() const;
    static const wxULongLong_t InvalidSize;

    // Description
    void SetDescription(const wxString& description);
    const wxString& GetDescription() const { return m_description; }

    // Packages
    void AddPackage(Package* package);
    void RemovePackage(Package* package);

    PackageList GetPackages();

    // Dependencies
    void AddDependency(Dependency* depends);
    void RemoveDependency(Dependency* depends);

    DependencyList GetDependencies();

    // Dirty
    void MarkDirty(bool dirty = true);
    bool IsDirty() const { return m_dirty; };

protected:
    // Information
    wxString m_checksum;
    wxULongLong_t m_size;
    wxString m_description;
    PackageList m_packages;
    DependencyList m_dependencies;
    bool m_dirty;
};


#endif // Header guard



