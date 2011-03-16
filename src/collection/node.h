// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_COLLECTION_NODE_H
#define __FCMAN_COLLECTION_NODE_H


// Requirements
#include <list>

#include <wx/defs.h>
#include <wx/string.h>


class WXDLLIMPEXP_XML wxXmlNode;

class Directory;
class Collection;


// Node base class
class Node;
typedef std::list<Node*> NodeList;

class Node
{
public:
    // ctor/dtor
    Node();
    virtual ~Node();

    // Information
    const wxString& GetName() const { return m_name; }
    const wxString& GetFullName() const { return m_fullname; }
    const wxString& GetFullPath() const { return m_fullpath; }
    wxString GetFullName(Directory* parent, const wxString& newname = wxEmptyString);

    const Directory* GetParent() const { return m_parent; }
    Directory* GetParent() { return m_parent; }

    const Collection* GetCollection() const { return m_collection; }
    Collection* GetCollection() { return m_collection; }


    // Save to an XML node
    virtual wxXmlNode* Save() = 0;

    // Actions
    virtual bool Exists() const = 0;
    virtual bool CanMove(Directory* parent);
    virtual bool Move(Directory* parent);
    virtual bool CanDelete();
    virtual bool Delete();
    virtual bool CanRename(const wxString& name);
    virtual bool Rename(const wxString& name);

    // Reset cache information
    virtual void Reset();

protected:
    // Information
    wxString m_name;
    wxString m_fullname;
    wxString m_fullpath;

    Directory* m_parent;
    Collection* m_collection;

private:
    // Make no copy/assign
    Node(const Node& copy);
    Node& operator=(const Node& rhs);


friend class Directory;
};


#endif // Header guard



