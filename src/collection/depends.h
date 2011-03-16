// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_COLLECTION_DEPENDS_H
#define __FCMAN_COLLECTION_DEPENDS_H


// Requirements
#include <list>

#include <wx/defs.h>
#include <wx/string.h>

#include "version.h"


class WXDLLIMPEXP_XML wxXmlNode;

class File;
class Package;


// Dependency object
class Dependency;
typedef std::list<Dependency*> DependencyList;

class Dependency
{
public:
    // ctor/dtor
    Dependency();
    Dependency(wxXmlNode* node);

    ~Dependency();

    // Information
    void SetName(const wxString& name);
    const wxString& GetName() const { return m_name; }

    void SetMinVersion(const wxString& version);
    const wxString& GetMinVersion() const { return m_minVersion.Get(); }
    
    void SetMaxVersion(const wxString& version);
    const wxString& GetMaxVersion() const { return m_maxVersion.Get(); }

    wxString GetDisplayString() const;

    bool Check(Package* package) const;

    // Actions
    wxXmlNode* Save();

    void Delete();

protected:
    // Information
    File* m_file;
    wxString m_name;
    Version m_minVersion;
    Version m_maxVersion;

private:
    // No copy or assign
    Dependency(const Dependency& copy);
    Dependency& operator=(const Dependency& rhs);
    

friend class File;
};


#endif // Header guard



