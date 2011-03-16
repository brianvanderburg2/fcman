// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_DIR_NODE_H
#define __FCMAN_DIR_NODE_H


// Requirements
#include <list>

#include <wx/defs.h>
#include <wx/string.h>

#include "node.h"
#include "file.h"


// Directory class
class Directory;
typedef std::list<Directory*> DirectoryList;

class Directory : public Node
{
public:
    // ctor/dtor
    Directory();
    Directory(wxXmlNode* node);

    virtual ~Directory();

    // Save to an XML node
    virtual wxXmlNode* Save();

    // Actions
    virtual bool Exists() const;
    virtual bool CanMove(Directory* parent);

    // Reset cache information
    virtual void Reset();

    // Information
    void AddChild(Node* node);
    void RemoveChild(Node* node, bool reset = true);

    NodeList GetChildren(bool recursive = false);
    DirectoryList GetDirectories(bool recursive = false);
    FileList GetFiles(bool recursive = false);

    bool HasDirectories() const;
    bool HasFiles() const;

    bool HasDirectory(const wxString& name) const;
    bool HasFile(const wxString& name) const;

protected:
    // Information
    NodeList m_children;

};


#endif // Header guard



